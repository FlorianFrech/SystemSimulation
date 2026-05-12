"""Co-simulation system orchestration and management.

This module provides the ``System`` class, which is the central orchestrator
for heterogeneous co-simulation. It manages components, connections, execution
order computation, and delegates simulation stepping to pluggable algorithms.

Key Responsibilities:
    - **Component Management**: Register and organize ``CoSimComponent`` instances
    - **Connection Validation**: Type and unit compatibility checking between ports
    - **Graph Analysis**: Build dependency graphs and detect algebraic loops
    - **Execution Ordering**: Compute parallelizable generations using topological sort
    - **Algorithm Delegation**: Step simulation using Jacobi, Gauss-Seidel, or Hybrid algorithms
    - **Event Routing**: Dispatch events between components via event connections
    - **History Aggregation**: Collect time-series data from all components

Typical Usage:
    Building and running a co-simulation::

        from syssimx import System, Connection
        from syssimx.components import FMUComponent

        # Create system
        system = System(name="ControlledPendulum")

        # Add components
        pendulum = FMUComponent("Pendulum", fmu_path="Pendulum.fmu")
        controller = FMUComponent("PID", fmu_path="Controller.fmu")
        system.add_component(pendulum)
        system.add_component(controller)

        # Define connections
        system.add_connection(Connection(
            src_comp="Pendulum", src_port="angle",
            dst_comp="PID", dst_port="measurement"
        ))
        system.add_connection(Connection(
            src_comp="PID", src_port="control",
            dst_comp="Pendulum", dst_port="torque"
        ))

        # Initialize and run
        system.initialize(t0=0.0)
        system.run(t0=0.0, tf=10.0, dt=0.001)

        # Retrieve results
        history = system.get_history()

See Also:
    :class:`Connection`: Signal connections between component ports
    :class:`EventConnection`: Event routing between components
    :mod:`syssimx.system.algorithms`: Stepping algorithm implementations
    :mod:`syssimx.system.graph`: Graph analysis utilities
"""

from __future__ import annotations

import logging
import timeit
from typing import Any

import networkx as nx

from ..core.base import CoSimComponent
from ..core.events import Event
from ..core.history import SystemHistory
from ..core.port import PortSpec
from . import graph
from .algorithms.base import Algorithm
from .algorithms.gauss_seidel import GaussSeidelAlgorithm
from .algorithms.hybrid import HybridAlgorithm
from .algorithms.ijcsa import solve_algebraic_scc_ijcsa
from .connection import Connection, EventConnection

_ports_compatible = PortSpec.compatible

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------
# System Class
# ----------------------------------------------------------------------------
class System:
    """Central orchestrator for heterogeneous co-simulation systems.

    The ``System`` class manages a collection of interconnected
    ``CoSimComponent`` instances, validates their connections, computes
    execution order, and coordinates simulation stepping through a
    pluggable algorithm.

    Attributes:
        name (str): Identifier for this system.
        components (dict[str, CoSimComponent]): Registered components by name.
        connections (list[Connection]): Signal connections between components.
        event_connections (list[EventConnection]): Event routing connections.
        graph (nx.MultiDiGraph): Complete connection graph (including delayed).
        groups (dict[str, list[CoSimComponent]]): Components organized by group.
        execution_order (list[list[str]]): Topologically sorted generations.
            Each generation contains components that can execute in parallel.
        algebraic_loops (list[list[str]]): Detected algebraic loops (SCCs > 1).
        algorithm (Algorithm): Stepping algorithm (Gauss-Seidel, Jacobi, Hybrid).
        history (SystemHistory): Aggregated time-series data from all components.
        is_initialized (bool): Whether ``initialize()`` has been called.
        t (float): Current simulation time.

    Example:
        Creating a simple two-component system::
    >>>     system = System("Feedback")
    >>>     system.add_component(plant)
    >>>     system.add_component(controller)
    >>>     system.add_connection(Connection(
    >>>         src_comp="plant", src_port="y",
    >>>         dst_comp="controller", dst_port="measurement"
    >>>     ))
    >>>     system.initialize(t0=0.0)
    >>>     system.run(t0=0.0, tf=10.0, dt=0.01)

    See Also:
        :class:`Connection`: Signal connection specification
        :class:`Algorithm`: Base class for stepping algorithms
    """

    def __init__(self, name: str):
        """Initialize a new co-simulation system.

        Args:
            name: Identifier for this system. Used in logging and
                history tracking.

        Example:
            >>> system = System("ControlledPendulum")
            >>> system.name
            'ControlledPendulum'
        """
        self.name = name
        self.components: dict[str, CoSimComponent] = {}
        self.connections: list[Connection] = []
        self.event_connections: list[EventConnection] = []
        self.graph = nx.MultiDiGraph()  # All connections (including delayed)
        self._dag = nx.DiGraph()  # Zero-delay connections only

        self.groups: dict[str, list[CoSimComponent]] = {}
        self.execution_order: list[list[str]] = []  # [ [comp names in gen0], [gen1], ...]
        self.execution_idx: dict[str, int] = {}  # comp name -> gen index

        # Algebraic loop diagnostics (SCCs with size > 1 on the direct feed-through graph)
        self.algebraic_loops: list[list[str]] = []  # Detected algebraic loops (if any)
        self._scc_index: dict[str, int] = {}  # comp name -> scc index

        # Pre-computed connection lookups
        self._incoming_by_dst: dict[str, list[Connection]] = {}
        self._input_sources: dict[str, dict[str, Connection]] = {}
        self._event_targets_by_source: dict[tuple[str, str], list[str]] = {}

        # Algorithm
        self.algorithm: Algorithm = GaussSeidelAlgorithm()

        # History Management
        self.history = SystemHistory(system_name=name)

        self.is_initialized: bool = False
        self.t = 0.0

    # ----------------------------------------------------------------------------
    # Algorithm
    # ----------------------------------------------------------------------------
    def set_algorithm(self, algorithm: Algorithm) -> None:
        """Set the co-simulation stepping algorithm.

        The algorithm determines how components are stepped during
        simulation. Available algorithms include:

        - ``GaussSeidelAlgorithm``: Sequential stepping (default)
        - ``JacobiAlgorithm``: Parallel stepping with delayed inputs
        - ``HybridAlgorithm``: Event-driven with bisection localization

        Args:
            algorithm: An instance implementing the ``Algorithm`` interface.

        Raises:
            TypeError: If ``algorithm`` doesn't implement ``Algorithm``.

        Example:
            >>> from syssimx.system.algorithms import JacobiAlgorithm
            >>> system.set_algorithm(JacobiAlgorithm())

        Note:
            If components with event indicators are detected during
            ``initialize()``, the algorithm is automatically upgraded
            to ``HybridAlgorithm``.
        """
        if not isinstance(algorithm, Algorithm):
            raise TypeError("algorithm must implement Algorithm")
        self.algorithm = algorithm

    # ----------------------------------------------------------------------------
    # Register components
    # ----------------------------------------------------------------------------
    def add_component(self, component: CoSimComponent):
        """Register a component with the system.

        Components must be added before connections can reference them.
        Each component's history is automatically registered with the
        system's history tracker.

        Args:
            component: A ``CoSimComponent`` instance to add. Its ``name``
                attribute must be unique within this system.

        Raises:
            RuntimeError: If called after ``initialize()``.
            ValueError: If a component with the same name already exists.

        Example:
            >>> pendulum = FMUComponent("Pendulum", fmu_path="model.fmu")
            >>> system.add_component(pendulum)
            >>> "Pendulum" in system.components
            True

        Note:
            If the component has a ``group`` attribute set, it will be
            added to ``system.groups[group]`` for visual organization.
        """
        if self.is_initialized:
            raise RuntimeError("Cannot add components after system initialization.")

        if component.name in self.components:
            raise ValueError(f"Component '{component.name}' already in system.")
        self.components[component.name] = component

        # Register component history
        self.history.add_component(component.name, component.history)

        if component.group:
            self.groups.setdefault(component.group, []).append(component)

    # ----------------------------------------------------------------------------
    # Connections
    # ----------------------------------------------------------------------------
    def _validate_connection(self, c: Connection) -> None:
        # 1) existence
        if c.src_comp not in self.components or c.dst_comp not in self.components:
            raise ValueError(
                f"Both '{c.src_comp}' and '{c.dst_comp}' must be added to the system before connecting them."
            )

        src = self.components[c.src_comp]
        dst = self.components[c.dst_comp]

        # 2) port existence
        if c.src_port not in src.output_specs:
            raise KeyError(
                f"Source port '{c.src_port}' is not an OUTPUT port of component '{src.name}'."
            )
        if c.dst_port not in dst.input_specs:
            raise KeyError(
                f"Destination port '{c.dst_port}' is not an INPUT port of component '{dst.name}'."
            )

        src_ps: PortSpec = src.output_specs[c.src_port]
        dst_ps: PortSpec = dst.input_specs[c.dst_port]

        # 3) type and unit compatibility
        if not _ports_compatible(src_ps, dst_ps):
            src_unit = src_ps.unit if src_ps.unit else "unitless"
            dst_unit = dst_ps.unit if dst_ps.unit else "unitless"
            raise TypeError(
                f"Port incompatibility: {c.src_comp}.{c.src_port} ({src_ps.type}, {src_unit}) "
                f"-> {c.dst_comp}.{c.dst_port} ({dst_ps.type}, {dst_unit})"
            )

        # 5) duplicate and single-assignment checks
        for existing in self.connections:
            same_source = (
                existing.src_comp == c.src_comp
                and existing.src_port == c.src_port
            )
            same_destination = (
                existing.dst_comp == c.dst_comp
                and existing.dst_port == c.dst_port
            )

            if same_source and same_destination:
                raise ValueError(
                    f"Duplicate connection: {c.src_comp}.{c.src_port} -> {c.dst_comp}.{c.dst_port}"
                )

            if same_destination:
                raise ValueError(
                    f"Input port already connected: {c.dst_comp}.{c.dst_port} is already driven by "
                    f"{existing.src_comp}.{existing.src_port}; cannot also connect "
                    f"{c.src_comp}.{c.src_port}."
                )

    def add_connection(self, connection: Connection) -> None:
        """Add a signal connection between two components.

        Validates port existence, type compatibility, and unit
        compatibility before registering the connection.

        Args:
            connection: A ``Connection`` specifying source and destination
                component/port pairs.

        Raises:
            ValueError: If source or destination component not in system,
                or if connection is a duplicate.
            KeyError: If specified ports don't exist on the components.
            TypeError: If port types or units are incompatible.

        Example:
            >>> system.add_connection(Connection(
            ...     src_comp="Sensor", src_port="value",
            ...     dst_comp="Controller", dst_port="measurement"
            ... ))

        See Also:
            :class:`Connection`: Connection specification class
            :meth:`add_event_connection`: For event-based connections
        """
        self._validate_connection(connection)
        self.connections.append(connection)
        self._incoming_by_dst.clear()
        self._input_sources.clear()

    # ----------------------------------------------------------------------------
    # Event Connections
    # ----------------------------------------------------------------------------
    def _validate_event_connection(self, connection: EventConnection) -> None:
        """Validate an event connection before registration.

        Performs the following checks:

        1. Source component exists in the system
        2. Target component exists in the system
        3. Event indicator is registered on the source component
        4. No duplicate connections exist

        Args:
            connection: The ``EventConnection`` to validate.

        Raises:
            ValueError: If source or target component not in system,
                or if connection is a duplicate.
            KeyError: If the event indicator is not registered on the
                source component.

        Note:
            Event subscription on the target is handled automatically
            by ``add_event_connection()``, not during validation.
        """
        if connection.src_comp not in self.components:
            raise ValueError(f"Event source '{connection.src_comp}' is not in the system.")
        if connection.dst_comp not in self.components:
            raise ValueError(f"Event target '{connection.dst_comp}' is not in the system.")

        source = self.components[connection.src_comp]
        event_name = connection.src_port

        # Check event indicator exists on source
        if event_name not in source.event_indicators:
            raise KeyError(
                f"Event indicator '{event_name}' not found on source component '{source.name}'. "
                f"Register it via: source.add_event_indicator(name='{event_name}', func=..., direction=...)"
            )

        # Check for duplicate connections
        for existing in self.event_connections:
            if existing.key() == connection.key():
                raise ValueError(
                    f"Duplicate event connection: {connection.src_comp}:{connection.event_name} -> {connection.target_comp}"
                )

    def add_event_connection(self, connection: EventConnection) -> None:
        """Add an event connection with automatic target subscription.

        Registers an event connection and automatically subscribes the
        target component to receive the event. This eliminates the need
        for manual ``Event`` object creation and ``subscribe_event()`` calls.

        Args:
            connection: ``EventConnection`` specifying the source component's
                event indicator and the target component to notify.

        Raises:
            ValueError: If source/target not in system or duplicate connection.
            KeyError: If event indicator not registered on source component.

        Example:
            >>> # Ball emits 'bounce' event, floor handles it
            >>> system.add_event_connection(EventConnection(
            ...     src_comp="Ball", event_name="bounce",
            ...     dst_comp="Floor"
            ... ))

        Note:
            The target component must implement ``_handle_events_internal()``
            to respond to the event when it fires.

        See Also:
            :class:`EventConnection`: Event connection specification
            :meth:`dispatch_event`: Manual event dispatching
        """
        self._validate_event_connection(connection)

        # Auto-subscribe the target component to this event
        source = self.components[connection.src_comp]
        target = self.components[connection.dst_comp]
        event_name = connection.event_name

        # Get direction from event indicator
        direction = source.event_indicators[event_name].direction

        # Create Event object for subscription (source, name, direction)
        event = Event(name=event_name, source=connection.src_comp, direction=direction)

        # Subscribe target if not already subscribed
        already_subscribed = any(
            e.name == event_name and e.source == connection.src_comp
            for e in target.event_subscriptions
        )
        if not already_subscribed:
            target.event_subscriptions.append(event)

        # Register the connection
        self.event_connections.append(connection)
        key = (connection.src_comp, connection.src_port)
        self._event_targets_by_source.setdefault(key, []).append(connection.dst_comp)

    def get_event_targets(self, source_comp: str, event_name: str) -> list[str]:
        """Get component names that receive a specific event.

        Args:
            source_comp: Name of the component emitting the event.
            event_name: Name of the event indicator.

        Returns:
            List of component names subscribed to this event.
            Returns empty list if no subscribers.
        """
        return self._event_targets_by_source.get((source_comp, event_name), []).copy()

    def dispatch_event(self, event: Event, t: float, notify: bool = True) -> list[str]:
        """Dispatch an event to all subscribed components.

        Resolves event listeners based on registered event connections
        and optionally notifies them by calling their ``handle_event()``
        method.

        Args:
            event: The ``Event`` object containing source and event name.
            t: Time at which the event occurred.
            notify: If ``True``, calls ``handle_event()`` on each target.
                If ``False``, only returns the target list without notifying.

        Returns:
            List of component names that are subscribed to this event.

        Raises:
            ValueError: If the event source is not in the system.

        Example:
            >>> event = Event(name="threshold", source="Sensor")
            >>> targets = system.dispatch_event(event, t=1.5)
            >>> print(targets)
            ['Controller', 'Logger']
        """
        if event.source not in self.components:
            raise ValueError(f"Event source '{event.source}' is not in the system.")

        targets = self.get_event_targets(event.source, event.name)
        if notify:
            for comp_name in targets:
                self.components[comp_name].handle_event([event.name], t)
        return targets

    # ----------------------------------------------------------------------------
    # Graphs
    # ----------------------------------------------------------------------------
    def build_graphs(self) -> None:
        """Build dependency graphs from registered connections.

        Constructs two graph representations:

        1. ``self.graph``: Complete ``MultiDiGraph`` with all connections,
           including delayed connections (for visualization)
        2. ``self._dag``: ``DiGraph`` with only zero-delay, direct-feedthrough
           connections (for execution ordering)

        Also detects algebraic loops as strongly connected components (SCCs)
        with more than one node on the direct-feedthrough graph.

        Note:
            Called automatically during ``initialize()``. The detected
            algebraic loops are stored in ``self.algebraic_loops``.

        See Also:
            :mod:`syssimx.system.graph`: Graph construction utilities
        """
        graph.build_graphs(self)

    def compute_execution_order(self) -> None:
        """Compute parallelizable execution order from the dependency graph.

        Performs a topological sort on the zero-delay dependency DAG to
        produce generations of components. Components within the same
        generation have no dependencies on each other and can execute
        in parallel.

        The result is stored in ``self.execution_order`` as a list of
        lists, where each inner list contains component names in one
        generation.

        Example:
            After calling::

                system.execution_order = [
                    ['Source', 'Reference'],      # Generation 0
                    ['Controller'],               # Generation 1
                    ['Plant'],                    # Generation 2
                    ['Sensor']                    # Generation 3
                ]

        See Also:
            :mod:`syssimx.system.graph`: Execution order computation
        """
        graph.compute_execution_order(self)

    def classify_components(self) -> dict[str, list[CoSimComponent]]:
        """Classify components by their hybrid simulation capabilities.

        Categorizes all components based on whether they have event
        indicators, event subscriptions, or neither. This classification
        is used to determine if hybrid simulation is needed.

        Returns:
            Dictionary with the following keys:

            - ``"event_sources"``: Components with event indicators
              (require rollback support for bisection)
            - ``"event_listeners"``: Components subscribed to events
              (will receive event notifications)
            - ``"continuous_only"``: Components without any hybrid
              capabilities (pure continuous dynamics)

        Note:
            A component can be both an event source and an event listener.
            The categorization is stored in instance attributes
            ``self.event_sources``, ``self.event_listeners``, and
            ``self.continuous_only``.
        """
        self.event_sources: list[CoSimComponent] = []
        self.event_listeners: list[CoSimComponent] = []
        self.continuous_only: list[CoSimComponent] = []

        for comp in self.components.values():
            if comp.has_state_events:
                self.event_sources.append(comp)
            if comp.has_event_subscriptions:
                self.event_listeners.append(comp)
            if not comp.has_state_events and not comp.has_event_subscriptions:
                self.continuous_only.append(comp)
        return {
            "event_sources": self.event_sources,
            "event_listeners": self.event_listeners,
            "continuous_only": self.continuous_only,
        }

    # ----------------------------------------------------------------------------
    # Simulation Lifecycle
    # ----------------------------------------------------------------------------
    def initialize(self, t0: float) -> None:
        """Initialize the system and all components at start time.

        Performs the complete initialization sequence:

        1. Classifies components and auto-selects ``HybridAlgorithm``
           if event sources are detected
        2. Creates port state objects for all components so that
           feedthrough detection and input propagation can work
        3. Detects direct feedthrough for pure-Python components via
           perturbation (FMU components already have this from their
           model description)
        4. Builds dependency graphs and computes execution order;
           algebraic loops are identified from zero-delay edges
        5. Iterates over generations in execution order:

           a. Propagates initial input values from upstream outputs
              into the generation's input port states

           b. Initializes components (FMUs apply stored port values
              via ``_apply_input_starts`` during init mode)

           c. Solves algebraic loops within the generation

           d. Performs a zero-step (dt=0) to establish consistent
              initial outputs for downstream generations

        This ordering ensures that each generation receives consistent
        initial values from already-initialized upstream components
        before entering FMU initialization mode.

        Args:
            t0: Initial simulation time in seconds.

        Example:
            >>> system.add_component(plant)
            >>> system.add_component(controller)
            >>> system.add_connection(connection)
            >>> system.initialize(t0=0.0)
            >>> system.is_initialized
            True

        Note:
            Must be called after all components and connections are added,
            but before ``run()``. Calling ``initialize()`` locks the system
            against further component additions.
        """
        self.t = t0

        # 1) Classify components and auto-select hybrid algorithm
        self.classify_components()
        if self.event_sources:
            self.algorithm = HybridAlgorithm()

        # 2) Ensure all components have port states created so that
        #    _detect_direct_feedthrough() can call evaluate_outputs() and
        #    _set_inputs_for_generation can write to them before initialize().
        #    For FMU components ports already exist (created in __init__);
        #    _initialize_ports_from_specs skips already-existing ports.
        for comp in self.components.values():
            comp._initialize_ports_from_specs()

        # 3) Detect direct feedthrough for components that haven't computed
        #    it yet.  FMU components populate this from modelDescription.xml
        #    in __init__(); pure-Python components need perturbation-based
        #    detection here so that build_graphs() can correctly identify
        #    zero-delay edges and algebraic loops.
        for comp in self.components.values():
            if not comp.direct_feedthrough:
                comp._detect_direct_feedthrough()

        # 4) Build dependency graphs and compute execution order
        self.build_graphs()
        self.compute_execution_order()

        # 5) Initialize generation by generation in execution order
        for gen in self.execution_order:
            # 5a) Propagate upstream outputs into this generation's input ports.
            #     Components are not yet initialized, so values are written
            #     directly to PortState objects (no FMU instance needed).
            self._set_inputs_for_generation(gen, t0)

            # 5b) Initialize components in this generation.
            #     For FMU components, _apply_input_starts() will push the
            #     port state values into the FMU during initialization mode.
            for comp_name in gen:
                self.components[comp_name].initialize(t0)

            # 5c) Solve algebraic loops within this generation
            gen_set = set(gen)
            for loop in self.algebraic_loops:
                if set(loop).issubset(gen_set):
                    solve_algebraic_scc_ijcsa(self, loop, t0)

            # 5d) Zero-step to update outputs for downstream generations
            for comp_name in gen:
                self.components[comp_name].do_step(0, 0)

        self.is_initialized = True

    def _set_inputs_for_generation(self, gen: list[str], t: float) -> None:
        """Set input values for all components in a generation.

        For each component in the generation, retrieves values from
        connected source ports and sets them as inputs. This propagates
        signal values through the connection graph.

        If a component is not yet initialized (e.g. during the
        generation-based initialization sequence), values are written
        directly to the ``PortState`` objects so that they are available
        when the component's ``initialize()`` is called later.  For
        already-initialized components the regular ``set_inputs()`` path
        is used, which also pushes values into the underlying solver
        (e.g. an FMU instance).

        Args:
            gen: List of component names in the current generation.
            t: Current simulation time for timestamping inputs.

        Note:
            Only non-None source values are propagated. Components with
            no incoming connections or all-None sources receive no updates.
        """
        for comp_name in gen:
            comp = self.components[comp_name]
            to_set: dict[str, Any] = {}
            input_map = self._input_sources.get(comp_name, {})
            for dst_port, c in input_map.items():
                src_value = self.components[c.src_comp].outputs[c.src_port].get()
                if src_value is not None:
                    to_set[dst_port] = src_value

            if to_set:
                if comp._is_initialized:
                    comp.set_inputs(to_set, t=t)
                else:
                    # Component not yet initialized — write directly to port
                    # states so values are available for _apply_input_starts()
                    for port_name, value in to_set.items():
                        comp.inputs[port_name].set(value, t=t)

    # ----------------------------------------------------------------------------
    # Run System Simulation
    # ----------------------------------------------------------------------------
    def run(self, t0: float, tf: float, dt: float):
        """Run the simulation from start time to end time.

        Advances the simulation by repeatedly calling the algorithm's
        ``step()`` method with the specified time step size.

        Args:
            t0: Start time in seconds (should match ``initialize(t0)``).
            tf: End time in seconds.
            dt: Fixed time step size in seconds. The final step may be
                smaller to land exactly on ``tf``.

        Example:
            >>> system.initialize(t0=0.0)
            >>> system.run(t0=0.0, tf=10.0, dt=0.001)
            >>> # Simulation complete, retrieve history
            >>> history = system.get_history()

        Note:
            The algorithm may take sub-steps during event localization
            (Hybrid algorithm) or iteration (IJCSA for algebraic loops).
            The ``dt`` parameter controls the macro step size.
        """
        timer = timeit.default_timer
        logger.info(f"Starting simulation run from t={t0} to t={tf} with dt={dt}")
        t = t0
        self.t_end = tf
        start_time = timer()
        while t < tf - 1e-12:
            dt = min(dt, tf - t)
            self.algorithm.step(self, t, dt)
            t += dt
        end_time = timer()
        logger.info(f"Simulation completed in {end_time - start_time:.2f} seconds")

    # ----------------------------------------------------------------------------
    # Get history of all components
    # ----------------------------------------------------------------------------
    def get_history(self) -> dict[str, Any]:
        """Retrieve time-series history from all components.

        Collects the recorded output history from every component in
        the system, plus any event history records.

        Returns:
            Dictionary with the following structure:

            - Keys are component names, values are tuples of
              ``(time_array, values_dict)`` from ``get_history_arrays()``
            - Special key ``"Events"`` contains event occurrence records

        Example:
            >>> history = system.get_history()
            >>> t, values = history["Pendulum"]
            >>> plt.plot(t, values["angle"])
            >>> # Access events
            >>> events = history["Events"]

        See Also:
            :meth:`CoSimComponent.get_history_arrays`: Component history format
        """
        history: dict[str, Any] = {}
        for comp_name, comp in self.components.items():
            history[comp_name] = comp.get_history_arrays()
        history["Events"] = self.history.get_all_event_histories()
        return history

    # ----------------------------------------------------------------------------
    # Reset System
    # ----------------------------------------------------------------------------
    def reset(self) -> None:
        """Reset the system and all components to uninitialized state.

        Clears all component states, histories, and internal flags,
        allowing the system to be re-initialized from scratch.

        Example:
            >>> system.initialize(t0=0.0)
            >>> system.run(t0=0.0, tf=10.0, dt=0.01)
            >>> system.reset()
            >>> system.is_initialized
            False
        """
        for comp in self.components.values():
            comp.reset()
        self.history.clear()
        self.is_initialized = False
        self.t = 0.0
