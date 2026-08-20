"""Multi-component wrapper for heterogeneous model switching.

This module provides the ``MultiComponent`` class for wrapping multiple
interchangeable simulation models (e.g., FEM, OpenSim, FMU pendulum) under a
unified interface. It enables dynamic mode switching during simulation
with automatic state synchronization between models.

Key Features:
    - **Dynamic Mode Switching**: Switch between different simulation
      models at runtime based on custom criteria (time, cached outputs,
      events)
    - **State Synchronization**: Automatic state transfer and adaptation
      when switching between models with different interfaces
    - **Region Hysteresis**: Nonzero boundary bands prevent threshold chatter
    - **Port Unification**: Validates that all sub-models have compatible
      port interfaces
    - **Event Delegation**: Transparently delegates hybrid event detection
      to the currently active sub-component

Typical Use Cases:
    - Multi-fidelity simulation: Switch between high-fidelity FEM and
      reduced-order models based on accuracy requirements
    - Contact dynamics: Use detailed contact model only when contact
      is imminent, otherwise use simpler dynamics
    - Adaptive resolution: Increase model complexity in regions of
      interest, decrease elsewhere

Example:
    Creating a multi-model pendulum::

        class MasterPendulum(MultiComponent):
            def __init__(self, fem, opensim, fmu):
                super().__init__(
                    name="Pendulum",
                    models={"FEM": fem, "OpenSim": opensim, "FMU": fmu},
                    initial_mode="FEM",
                )

            def _adapt_state(self, state, target_mode):
                if target_mode == "FMU":
                    return {'q0': state['q'], 'omega0': state['omega']}
                return state

        # Use with declarative, event-localized regions
        pendulum = MasterPendulum(fem, opensim, fmu)
        pendulum.set_switch_regions(
            key=lambda comp: comp.outputs["theta"].get().magnitude,
            breakpoints=(-0.075, 0.075),
            modes=("FMU", "FEM", "FMU"),
            band=0.005,
        )

See Also:
    :class:`CoSimComponent`: Base class for all components
    :class:`SwitchRegions`: Immutable region switching configuration
"""

from __future__ import annotations

import logging
import math
from bisect import bisect_right
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from .base import CoSimComponent
from .events import InternalEventInfo
from .port import PortSpec

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Type Aliases
# -------------------------------------------------------------------
ModeKey = str  # e.g., "FEM", "OpenSim", "FMU"


# -------------------------------------------------------------------
# State Adapter Protocol (for incompatible component interfaces)
# -------------------------------------------------------------------
class StateAdapter(Protocol):
    """Protocol for adapting state between components with different interfaces.

    Implement this protocol to provide custom state translation logic
    when switching between models that use different state variable names,
    units, or representations.

    Example:
        >>> class FMUAdapter:
        ...     def adapt_state(self, source_state, target_component):
        ...         # FMU uses 'q0', 'omega0' instead of 'q', 'omega'
        ...         return {
        ...             'q0': source_state['q'],
        ...             'omega0': source_state['omega']
        ...         }
    """

    def adapt_state(
        self, source_state: dict[str, Any], target_component: CoSimComponent
    ) -> dict[str, Any]:
        """Convert state from source format to target component's format.

        Args:
            source_state: State dictionary from the source component,
                typically in the format returned by ``get_state()``.
            target_component: The component that will receive the
                adapted state via ``set_state()``.

        Returns:
            Adapted state dictionary compatible with the target
            component's ``set_state()`` method.
        """
        ...


@dataclass(frozen=True)
class _PreparedStateTransfer:
    """Validated target state waiting for one identity commit."""

    source_state: dict[str, Any]
    target_state: dict[str, Any]


@dataclass(frozen=True)
class RegionBoundary:
    """One physical boundary and its Schmitt-trigger band."""

    index: int
    breakpoint: float
    band: float

    @property
    def lower_threshold(self) -> float:
        return self.breakpoint - self.band

    @property
    def upper_threshold(self) -> float:
        return self.breakpoint + self.band

    def threshold_for(self, active_region_index: int) -> float:
        """Return the armed threshold for the current side of this boundary."""
        if active_region_index <= self.index:
            return self.upper_threshold
        return self.lower_threshold

    def target_region(self, direction: int) -> int:
        """Resolve the adjacent destination from crossing direction."""
        if direction == 1:
            return self.index + 1
        if direction == -1:
            return self.index
        raise ValueError("A region crossing direction must be -1 or +1.")


@dataclass(frozen=True, init=False)
class SwitchRegions:
    """Immutable, validated mapping from one scalar signal to model regions.

    Every physical boundary is stored once. Its active threshold is the upper
    band edge while the runtime region is below it and the lower band edge
    while the runtime region is above it.
    """

    key: Callable[[CoSimComponent], float]
    modes: tuple[ModeKey, ...]
    boundaries: tuple[RegionBoundary, ...]

    def __init__(
        self,
        key: Callable[[CoSimComponent], float],
        breakpoints: Sequence[float],
        modes: Sequence[ModeKey],
        band: float | Sequence[float],
    ) -> None:
        if not callable(key):
            raise TypeError("SwitchRegions.key must be callable.")

        points = tuple(float(value) for value in breakpoints)
        mode_keys = tuple(modes)
        if len(mode_keys) < 2:
            raise ValueError("SwitchRegions requires at least two model regions.")
        if len(points) != len(mode_keys) - 1:
            raise ValueError(
                f"Expected exactly {len(mode_keys) - 1} boundaries for "
                f"{len(mode_keys)} model regions, got {len(points)}."
            )
        if any(not math.isfinite(value) for value in points):
            raise ValueError("Region breakpoints must be finite.")
        if any(left >= right for left, right in zip(points, points[1:], strict=False)):
            raise ValueError("Region breakpoints must be strictly increasing.")
        if any(left == right for left, right in zip(mode_keys, mode_keys[1:], strict=False)):
            raise ValueError("Neighboring regions must use different models.")

        if isinstance(band, Sequence) and not isinstance(band, (str, bytes)):
            bands = tuple(float(value) for value in band)
        else:
            bands = (float(band),) * len(points)
        if len(bands) != len(points):
            raise ValueError(f"Expected exactly {len(points)} boundary bands, got {len(bands)}.")
        if any(not math.isfinite(value) or value <= 0.0 for value in bands):
            raise ValueError("Every region boundary requires a finite, nonzero positive band.")

        boundaries = tuple(
            RegionBoundary(index=index, breakpoint=point, band=bands[index])
            for index, point in enumerate(points)
        )
        if any(
            left.upper_threshold >= right.lower_threshold
            for left, right in zip(boundaries, boundaries[1:], strict=False)
        ):
            raise ValueError("Adjacent region bands must not overlap or touch.")

        object.__setattr__(self, "key", key)
        object.__setattr__(self, "modes", mode_keys)
        object.__setattr__(self, "boundaries", boundaries)

    @property
    def breakpoints(self) -> tuple[float, ...]:
        return tuple(boundary.breakpoint for boundary in self.boundaries)

    @property
    def bands(self) -> tuple[float, ...]:
        return tuple(boundary.band for boundary in self.boundaries)

    def initial_region(self, value: float) -> int:
        """Return the nominal region containing ``value`` at initialization."""
        if not math.isfinite(value):
            raise ValueError("The region switching signal must be finite.")
        return bisect_right(self.breakpoints, value)


# -------------------------------------------------------------------
# Abstract MultiComponent Base Class
# -------------------------------------------------------------------
class MultiComponent(CoSimComponent):
    """Abstract base class for components wrapping multiple interchangeable models.

    ``MultiComponent`` enables dynamic switching between different simulation
    models during runtime while presenting a unified interface to the rest
    of the co-simulation system. Each sub-model ("mode") can use a different
    solver, fidelity level, or physics representation.

    Subclass Responsibilities:
        1. Construct the sub-components and pass them to ``super().__init__``
           through the ``models`` argument together with ``initial_mode``.
        2. Override ``_adapt_state()`` for component-specific state translation.
        3. Configure :meth:`set_switch_regions` when runtime switching is required.

    Base Class Handles:
        - Port unification (validates all models have compatible ports)
        - Event-localized switching with region-band hysteresis
        - State synchronization during mode transitions
        - Input/output delegation to the active component
        - Event indicator delegation for hybrid simulation

    Attributes:
        models (dict[ModeKey, CoSimComponent]): Registry mapping mode keys
            (e.g., "FEM", "OpenSim") to component instances. Populated in
            ``__init__`` and fixed for the lifetime of the wrapper.
        active_mode (ModeKey): Key of the currently active model.
        active_comp (CoSimComponent): Reference to the currently active
            component instance. Always set after ``__init__``.
        state_adapters (dict[ModeKey, StateAdapter]): Optional per-mode
            state adapters for complex translation logic.
        sync_events (list): Log of mode switch events for debugging.

    Example:
        Minimal subclass implementation::

            class DualPendulum(MultiComponent):
                def __init__(self, detailed, simplified):
                    super().__init__(
                        "Pendulum",
                        models={"detailed": detailed, "simplified": simplified},
                        initial_mode="detailed",
                    )

                def _adapt_state(self, state, target_mode):
                    # Both models use same state format
                    return state

    See Also:
        :class:`CoSimComponent`: Parent class with full interface docs
        :class:`SwitchRegions`: Immutable region switching configuration
        :class:`StateAdapter`: Protocol for state translation
    """

    def __init__(
        self,
        name: str,
        models: dict[ModeKey, CoSimComponent],
        initial_mode: ModeKey,
        group: str | None = None,
    ):
        """Initialize a multi-component wrapper.

        Args:
            name: Unique identifier for this component in the system.
            models: Mapping of mode keys to component instances. Must
                contain at least ``initial_mode`` and must not be empty.
            initial_mode: Key of the model to activate initially. Must
                be a key in ``models``.
            group: Optional category for component organization.

        Raises:
            ValueError: If ``models`` is empty or ``initial_mode`` is not
                a key in ``models``.

        Example:
            >>> super().__init__(
            ...     name="Pendulum",
            ...     models={"FEM": fem, "FMU": fmu},
            ...     initial_mode="FEM",
            ...     group="Plant",
            ... )
        """
        if not models:
            raise ValueError(f"{name}: 'models' must not be empty")
        if initial_mode not in models:
            raise ValueError(
                f"{name}: initial_mode '{initial_mode}' not in models {list(models.keys())}"
            )

        super().__init__(name, label=name, group=group)

        # Model registry and the active model reference.
        self.models: dict[ModeKey, CoSimComponent] = models
        self._initial_mode: ModeKey = initial_mode
        self._active_mode: ModeKey = initial_mode

        # A configured region map owns runtime identity. ``None`` is valid
        # only before its one-time initialization reconciliation.
        self._switch_regions: SwitchRegions | None = None
        self.active_region_index: int | None = None
        self._region_boundaries_by_event: dict[str, RegionBoundary] = {}
        self._initializing_regions: bool = False

        # State adapters (optional): {mode_key: adapter}
        self.state_adapters: dict[ModeKey, StateAdapter] = {}

        # List of synchronization events (for logging/debugging)
        self.sync_events: list = []

        # Flag to prevent mode switching during event detection
        self._allow_mode_switching: bool = True

        # Latest input dict and timestamp seen by set_inputs. Used to
        # bring a newly activated model up to date during a mode switch
        # without forwarding inputs to inactive models on every step.
        self._latest_inputs: tuple[dict[str, Any], float | None] | None = None

        # When True, switch records in ``sync_events`` include the
        # pre-adaptation source state and the synchronized target state.
        # Default False because reading the target state calls
        # ``active_comp.get_state()`` once per switch, which can be
        # expensive for high-fidelity models.
        self.record_switch_state: bool = False

        # Previous and current state for synchronization
        self._prev_state: dict[str, Any] | None = None
        self._curr_state: dict[str, Any] | None = None

    @property
    def switch_regions(self) -> SwitchRegions | None:
        """Return the immutable region configuration, if one was declared."""
        return self._switch_regions

    @property
    def active_mode(self) -> ModeKey:
        """Return the active model key, derived from the active region when configured."""
        if self.switch_regions is None:
            return self._active_mode
        if self.active_region_index is None:
            if not self._is_initialized:
                return self._active_mode
            raise RuntimeError(f"{self.name}: Runtime region identity is not initialized.")
        if not 0 <= self.active_region_index < len(self.switch_regions.modes):
            raise RuntimeError(
                f"{self.name}: Invalid active_region_index {self.active_region_index}; "
                f"expected 0..{len(self.switch_regions.modes) - 1}."
            )
        return self.switch_regions.modes[self.active_region_index]

    @property
    def active_comp(self) -> CoSimComponent:
        """Return the component assigned to :attr:`active_mode`."""
        return self.models[self.active_mode]

    # -------------------------------------------------------------------
    # State Adaptation Hook
    # -------------------------------------------------------------------
    def _adapt_state(self, state: dict[str, Any], target_mode: ModeKey) -> dict[str, Any]:
        """Adapt state dictionary for the target model's interface.

        Subclasses must override this method to translate state between
        models that use different variable names, units, or representations.
        Called during mode switching to transform the current model's state
        into a format the target model can accept.

        Args:
            state: State dictionary from the current active component,
                as returned by ``get_state()``.
            target_mode: Key of the model being switched to.

        Returns:
            Adapted state dictionary compatible with the target model's
            ``set_state()`` method.

        Raises:
            NotImplementedError: If not overridden by subclass.

        Example:
            >>> def _adapt_state(self, state, target_mode):
            ...     if target_mode == "FMU":
            ...         # FMU uses initial condition naming
            ...         return {
            ...             'q0': state['q'],
            ...             'omega0': state['omega'],
            ...             'torque': state['torque']
            ...         }
            ...     return state  # Other models use standard naming

        Note:
            This is the primary extension point for handling heterogeneous
            model interfaces. If models share identical state formats,
            simply return ``state`` unchanged.
        """
        raise NotImplementedError(f"{self.name}: Subclass must implement _adapt_state()")

    # -------------------------------------------------------------------
    # Initialization Logic
    # -------------------------------------------------------------------
    def initialize(self, t0: float) -> None:
        """Initialize and reconcile a configured region map exactly once."""
        if self._is_initialized:
            return
        self._initializing_regions = self.switch_regions is not None
        try:
            super().initialize(t0)
        finally:
            self._initializing_regions = False
        if self.switch_regions is not None and self.active_region_index is None:
            raise RuntimeError(f"{self.name}: Initialization did not establish a runtime region.")

    def _initialize_component(self, t0: float) -> None:
        """Initialize all registered sub-components at time ``t0``.

        Models and the active component are fixed by ``__init__``. This
        hook only initializes each registered sub-component so that any
        of them is ready for activation on a later mode switch.

        Args:
            t0: Initial simulation time in seconds.

        Note:
            All sub-components are initialized, not just the active one.
        """
        for comp in self.models.values():
            if comp is not None:
                comp.initialize(t0)

    # -------------------------------------------------------------------
    # Port Unification and Validation
    # -------------------------------------------------------------------
    @staticmethod
    def _validate_port_compatibility(
        ref_spec: PortSpec, spec: PortSpec, model_name: str, port_name: str
    ) -> None:
        """Validate that two PortSpecs are compatible for MultiComponent use."""
        if ref_spec.name != port_name or spec.name != port_name:
            raise ValueError(
                f"Port name mismatch for '{port_name}' in model '{model_name}': "
                f"got '{spec.name}', expected '{port_name}'."
            )
        if ref_spec.direction != spec.direction:
            raise ValueError(
                f"Port direction mismatch for '{port_name}' in model '{model_name}': "
                f"{ref_spec.direction} vs {spec.direction}."
            )
        if ref_spec.type != spec.type:
            raise ValueError(
                f"Port type mismatch for '{port_name}' in model '{model_name}': "
                f"{ref_spec.type} vs {spec.type}."
            )
        if not PortSpec.compatible(ref_spec, spec):
            raise ValueError(
                f"Port unit/type incompatibility for '{port_name}' in model '{model_name}': "
                f"{ref_spec} vs {spec}."
            )

    # -------------------------------------------------------------------
    # Event-Localized Mode Switching
    # -------------------------------------------------------------------
    def set_switch_regions(
        self,
        key: Callable[[CoSimComponent], float],
        breakpoints: Sequence[float],
        modes: Sequence[ModeKey],
        band: float | Sequence[float],
    ) -> None:
        """Configure event-localized switching over ordered signal regions.

        One private bidirectional event indicator is generated per physical
        boundary. The indicator is armed at the far edge of its hysteresis
        band, according to :attr:`active_region_index`.
        """
        if self._is_initialized:
            raise RuntimeError(
                f"{self.name}: Switch regions must be declared before initialization."
            )
        if self.switch_regions is not None:
            raise RuntimeError(f"{self.name}: Switch regions are already declared.")
        regions = SwitchRegions(key, breakpoints, modes, band)
        unknown = sorted(set(regions.modes) - self.models.keys())
        if unknown:
            raise ValueError(f"{self.name}: Unknown region models: {unknown}.")
        without_rollback = sorted(
            mode for mode in set(regions.modes) if not self.models[mode].supports_rollback
        )
        if without_rollback:
            raise RuntimeError(
                f"{self.name}: Every region model must support rollback; missing: "
                f"{without_rollback}."
            )

        for boundary in regions.boundaries:
            name = f"region_boundary_{boundary.index}"
            if name in self.event_indicators or any(
                name in comp.event_indicators for comp in self.models.values()
            ):
                raise KeyError(f"{self.name}: Generated region event '{name}' collides.")

        self._switch_regions = regions
        for boundary in regions.boundaries:
            name = f"region_boundary_{boundary.index}"

            def indicator(comp: CoSimComponent, boundary: RegionBoundary = boundary) -> float:
                wrapper = comp
                if not isinstance(wrapper, MultiComponent):
                    raise TypeError("Region boundary indicators require a MultiComponent.")
                index = wrapper._require_active_region_index()
                threshold = boundary.threshold_for(index)
                return float(regions.key(wrapper)) - threshold

            CoSimComponent.add_event_indicator(self, name, indicator, direction=0)
            self._region_boundaries_by_event[name] = boundary

    def _require_active_region_index(self) -> int:
        """Return a valid runtime region or raise on inconsistent state."""
        regions = self.switch_regions
        if regions is None:
            raise RuntimeError(f"{self.name}: No switch regions are configured.")
        index = self.active_region_index
        if index is None or not 0 <= index < len(regions.modes):
            raise RuntimeError(
                f"{self.name}: Invalid runtime region {index!r}; initialization must establish "
                "one valid active_region_index."
            )
        return index

    def _resolve_region_target(self, event_names: list[str]) -> tuple[int, ModeKey] | None:
        """Resolve one region transition from boundary and localized direction."""
        if not self._allow_mode_switching:
            return None
        region_events = [name for name in event_names if name in self._region_boundaries_by_event]
        if not region_events:
            return None
        if len(region_events) != 1:
            raise RuntimeError(
                f"{self.name}: Expected one chronological region boundary, got {region_events}."
            )

        name = region_events[0]
        event = self._events_being_handled.get(name)
        direction = None if event is None else event.direction
        if direction not in (-1, 1):
            raise RuntimeError(
                f"{self.name}: Region event '{name}' has no localized crossing direction."
            )

        boundary = self._region_boundaries_by_event[name]
        source_index = self._require_active_region_index()
        expected_source = boundary.index if direction == 1 else boundary.index + 1
        if source_index != expected_source:
            raise RuntimeError(
                f"{self.name}: Boundary {boundary.index} crossed in direction {direction:+d} "
                f"from inconsistent region {source_index}; expected {expected_source}."
            )
        target_index = boundary.target_region(direction)
        assert self.switch_regions is not None
        return target_index, self.switch_regions.modes[target_index]

    def _unify_ports(self) -> None:
        """Adopt port specifications from active component and validate compatibility.

        Copies input and output port specifications from the active component
        to this ``MultiComponent``, then validates that all registered models
        have compatible port interfaces.

        Raises:
            ValueError: If any model is missing a required input or output
                port that exists in the active component's specification.

        Note:
            This ensures the ``MultiComponent`` presents a consistent interface
            regardless of which sub-model is active. All models must have at
            least the same ports as the active component (they may have more).
        """
        # Adopt active component's port specs. Generated region event ports are
        # preserved because no sub-model declares them.
        active_comp = self.active_comp
        own_event_specs = {
            name: spec
            for name, spec in self.output_specs.items()
            if name in self._region_boundaries_by_event
        }
        self.input_specs = active_comp.input_specs.copy()
        self.output_specs = active_comp.output_specs.copy()
        self.output_specs.update(own_event_specs)

        # Validate: all models must have compatible ports
        for mode_key, comp in self.models.items():
            if comp is None:
                continue

            # Check inputs
            for name, spec in self.input_specs.items():
                if name not in comp.input_specs:
                    raise ValueError(f"{self.name}: Model '{mode_key}' missing input port '{name}'")
                self._validate_port_compatibility(spec, comp.input_specs[name], mode_key, name)

            # Check outputs. Region event ports are owned by this wrapper and
            # are not expected on any sub-model.
            for name, spec in self.output_specs.items():
                if name in self._region_boundaries_by_event:
                    continue
                if name not in comp.output_specs:
                    raise ValueError(
                        f"{self.name}: Model '{mode_key}' missing output port '{name}'"
                    )
                self._validate_port_compatibility(spec, comp.output_specs[name], mode_key, name)

    # -------------------------------------------------------------------
    # Time Stepping
    # -------------------------------------------------------------------
    def _do_step_internal(self, t: float, dt: float) -> None:
        """Delegate one macro step to the active model.

        Args:
            t: Current simulation time in seconds.
            dt: Macro step size in seconds.

        Note:
            Mode switching can be temporarily disabled by setting
            ``_allow_mode_switching = False``. This is used by the hybrid
            algorithm during trial steps so that event detection does not
            change the active model while a rollback snapshot is valid.
        """
        if dt <= 0.0:
            self.active_comp._record_history = self._record_history
            self.active_comp.do_step(t, dt)
            return
        # Propagate the history-recording flag so that trial steps performed by
        # the hybrid algorithm (which disable recording on this MultiComponent)
        # also suppress recording on the active model's own history buffer.
        self.active_comp._record_history = self._record_history
        self.active_comp.do_step(t, dt)

    # -------------------------------------------------------------------
    # Mode Switching with State Synchronization
    # -------------------------------------------------------------------
    def _switch_mode(self, new_mode: ModeKey, t: float) -> None:
        """Switch to a new mode with state synchronization.

        This is the internal mode-key transition primitive. Region switching
        uses :meth:`_switch_region`, because a model key is not a region identity.

        Args:
            new_mode: Key of the mode to switch to. Must exist in
                ``self.models`` and be non-None.
            t: Current simulation time at which the switch occurs.

        Raises:
            ValueError: If ``new_mode`` is not in the models registry.
            RuntimeError: If the target model is ``None``.
        """
        if self.switch_regions is not None:
            raise RuntimeError(
                f"{self.name}: A configured region map must switch by region, not model key."
            )
        if new_mode not in self.models:
            raise ValueError(f"{self.name}: Unknown mode '{new_mode}'")
        new_comp = self.models[new_mode]
        if new_comp is None:
            raise RuntimeError(f"{self.name}: Model '{new_mode}' is not initialized")

        from_mode = self.active_mode
        prepared = self._perform_state_transfer(new_comp, new_mode, t)
        self._active_mode = new_mode
        self._capture_switch_event(t, from_mode, new_mode, prepared)
        logger.info("[%s] Switching: %s to %s @ t=%.4fs", self.name, from_mode, new_mode, t)

    def _switch_region(self, target_index: int, t: float, *, record: bool = True) -> None:
        """Commit one transition to an adjacent region."""
        regions = self.switch_regions
        if regions is None:
            raise RuntimeError(f"{self.name}: No switch regions are configured.")
        source_index = self._require_active_region_index()
        if abs(target_index - source_index) != 1:
            raise RuntimeError(
                f"{self.name}: Region transitions must be adjacent; got "
                f"{source_index} -> {target_index}."
            )

        from_mode = regions.modes[source_index]
        to_mode = regions.modes[target_index]
        new_comp = self.models[to_mode]
        prepared = self._perform_state_transfer(new_comp, to_mode, t)
        self._active_mode = to_mode
        self.active_region_index = target_index
        if record:
            self._capture_switch_event(t, from_mode, to_mode, prepared)
        logger.info("[%s] Switching: %s to %s @ t=%.4fs", self.name, from_mode, to_mode, t)

    def _perform_state_transfer(
        self, new_comp: CoSimComponent, new_mode: ModeKey, t: float
    ) -> _PreparedStateTransfer:
        """Prepare and validate ``new_comp`` without committing identity.

        Both the accepted wrapper/source and the inactive target are
        checkpointed before preparation. Any exception restores both exact
        checkpoints, including time, ports, history, and runtime metadata.
        The caller alone commits the active mode or region after this method
        returns successfully.

        Args:
            new_comp: The component instance that will become active.
            new_mode: Key of the target mode used by ``_adapt_state()``.
            t: Current simulation time.

        Returns:
            The source and validated target physical states for an eventual
            switch record.
        """
        source_checkpoint = self.checkpoint()
        target_checkpoint = new_comp.checkpoint()
        try:
            with self.trial_context():
                retrieved = self.active_comp.get_state()
                adapted = self._adapt_state(retrieved, new_mode)
                if self._latest_inputs is not None:
                    signals, t_inputs = self._latest_inputs
                    new_comp.set_inputs(signals, t_inputs)

                # Target preparation is deliberately ordered: import, validate,
                # publish target outputs, then return to the caller for commit.
                new_comp.set_state(adapted, t)
                new_comp.t = t
                synchronized = self._validate_imported_state(
                    retrieved, adapted, new_mode, new_comp, t
                )
                new_comp._update_output_states(t)
            return _PreparedStateTransfer(retrieved, synchronized)
        except Exception as transfer_error:
            rollback_errors: list[Exception] = []
            for component, checkpoint in (
                (new_comp, target_checkpoint),
                (self, source_checkpoint),
            ):
                try:
                    component.restore_checkpoint(checkpoint)
                except Exception as rollback_error:  # pragma: no cover - catastrophic backend fault
                    rollback_errors.append(rollback_error)
            if rollback_errors:
                raise RuntimeError(
                    f"{self.name}: State transfer to '{new_mode}' failed and rollback "
                    f"reported {len(rollback_errors)} additional error(s)."
                ) from transfer_error
            raise

    def _validate_imported_state(
        self,
        source_state: dict[str, Any],
        adapted_state: dict[str, Any],
        target_mode: ModeKey,
        target: CoSimComponent,
        t: float,
    ) -> dict[str, Any]:
        """Validate a prepared target and return its readable physical state.

        The default contract requires the imported state to be readable again.
        Domain-specific composites can override this hook to check conserved
        quantities, projection residuals, units, or tolerances before commit.
        """
        return target.get_state()

    def _capture_switch_event(
        self,
        t: float,
        from_mode: ModeKey,
        to_mode: ModeKey,
        prepared: _PreparedStateTransfer,
    ) -> None:
        """Append one record of the completed switch to ``sync_events``.

        Always logs the time, source mode, and target mode. When
        ``self.record_switch_state`` is ``True``, the record also
        includes the already prepared source and validated target states.
        ``record_switch_state`` defaults to ``False`` and should be enabled
        only for debugging synchronization issues.

        Args:
            t: Time at which the switch occurred.
            from_mode: Mode key that was active before the switch.
            to_mode: Mode key that is active after the switch.
            prepared: Validated source and target states from the transaction.
        """
        record: dict[str, Any] = {
            "time": t,
            "from_mode": from_mode,
            "to_mode": to_mode,
        }
        if self.record_switch_state:
            record["retrieved"] = prepared.source_state
            record["now"] = prepared.target_state
        self.sync_events.append(record)

    # -------------------------------------------------------------------
    # Input/Output Delegation
    # -------------------------------------------------------------------
    def set_inputs(self, signals: dict[str, Any], t: float | None = None) -> None:
        """Forward inputs to the active sub-component and cache them.

        Only the active model receives inputs each step. The cached
        ``(signals, t)`` pair is replayed onto the target model inside
        ``_perform_state_transfer`` when a mode switch occurs, so the
        newly activated model sees the same inputs the outgoing one had.

        Args:
            signals: Dictionary mapping input port names to values.
            t: Optional timestamp for the input values.
        """
        self._latest_inputs = (signals, t)
        self.active_comp.set_inputs(signals, t)

    def _update_output_states(
        self, t: float | None = None, event_names: list[str] | None = None
    ) -> None:
        """Copy output values from the active component to this wrapper.

        Reads all output values from the active sub-component and writes
        them to this ``MultiComponent``'s output ports. Also handles event
        port updates based on which events fired.

        Args:
            t: Current simulation time for timestamping port values.
            event_names: List of event names that just occurred. Event
                ports matching these names are set to ``True``; others
                are set to ``False``.

        Note:
            This ensures the ``MultiComponent`` always reflects the active
            component's outputs, regardless of which model is active.
        """
        self._copy_active_outputs(t)
        if self._initializing_regions and self.active_region_index is None:
            self._reconcile_initial_region(t)
            self._copy_active_outputs(t)
        self._apply_event_ports(t, event_names)

    def _copy_active_outputs(self, t: float | None) -> None:
        """Publish the active model's ordinary outputs on the wrapper."""
        active_comp = self.active_comp
        for name in self.output_specs:
            # Switch-indicator event ports exist only on this wrapper; they are
            # driven by ``_apply_event_ports`` below, not by the active model.
            if name not in active_comp.outputs:
                continue
            value = active_comp.outputs[name].get()
            if value is not None:
                self.outputs[name].set(value, t=t)

    def _reconcile_initial_region(self, t: float | None) -> None:
        """Derive region identity once from the initialized switching signal."""
        regions = self.switch_regions
        if regions is None:
            return
        value = float(regions.key(self))
        target_index = regions.initial_region(value)
        target_mode = regions.modes[target_index]
        if target_mode != self._active_mode:
            self._perform_state_transfer(self.models[target_mode], target_mode, float(t or 0.0))
        self._active_mode = target_mode
        self.active_region_index = target_index

    def evaluate_outputs(self, inputs: dict[str, Any], t: float | None = None) -> dict[str, Any]:
        saved = self._allow_mode_switching
        self._allow_mode_switching = False
        try:
            outputs = self.active_comp.evaluate_outputs(inputs, t=t)
            for name, value in outputs.items():
                if name in self.outputs and value is not None:
                    self.outputs[name].set(value, t=t)
            return outputs
        finally:
            self._allow_mode_switching = saved

    # -------------------------------------------------------------------
    # State Management Delegation
    # -------------------------------------------------------------------
    def set_state(self, state: dict[str, Any], t: float) -> None:
        """Set state on the active component with adaptation.

        Adapts the provided state for the active model's interface using
        ``_adapt_state()``, then delegates to the active component.

        Args:
            state: State dictionary to set. Will be adapted for the
                active model's expected format.
            t: Time at which to set the state.

        See Also:
            :meth:`_adapt_state`: State translation hook
        """
        adapted_state = self._adapt_state(state, self.active_mode)
        self.active_comp.set_state(adapted_state, t)

    def get_state(self) -> dict[str, Any]:
        """Get the current state from the active component.

        Returns:
            State dictionary from the active sub-component, in that
            component's native format.

        Note:
            The returned state format depends on which model is active.
            Use ``_adapt_state()`` if you need to translate to another
            model's format.
        """
        return self.active_comp.get_state()

    # -------------------------------------------------------------------
    # Hybrid Capabilities Delegation
    # -------------------------------------------------------------------
    def add_event_indicator(self, name: str, func: Callable, direction: int = 0) -> None:
        """Register an event indicator on all sub-components.

        Adds the event indicator to every sub-component that supports
        rollback, ensuring consistent event detection regardless of
        which model is active.

        Args:
            name: Unique name for the event indicator.
            func: Callable ``(component) -> float`` that returns the
                indicator value. Should work with any sub-component.
            direction: Zero-crossing direction: -1 (falling), 0 (both),
                +1 (rising).

        Note:
            The indicator function should access state through the
            unified interface (e.g., ``comp.get_outputs()``) rather
            than model-specific internals to work across all models.
        """
        for comp in self.models.values():
            if comp is not None and comp.supports_rollback:
                comp.add_event_indicator(name, func, direction)

        # Also add to self for port management
        super().add_event_indicator(name, func, direction)

    def evaluate_event_indicators(self) -> dict[str, float]:
        """Evaluate the active component's indicators and this wrapper's own.

        The returned mapping merges two sources. The active sub-model's
        indicators describe its physics, and this wrapper's generated region
        boundaries describe when the active model should be exchanged. Both are handed to
        the hybrid algorithm together, so a switch is localized by the same
        bisection that localizes a physical state event.

        Returns:
            Dictionary mapping indicator names to their current values. Empty
            if neither the active component nor this wrapper has indicators.
        """
        values: dict[str, float] = {}
        if self.active_comp.has_state_events:
            values.update(self.active_comp.evaluate_event_indicators())
        # Only generated region boundaries are evaluated here. Indicators added through
        # ``add_event_indicator`` are broadcast to the sub-models and kept on
        # this wrapper for port management only, so the active model above is
        # already their authoritative source.
        for name in self._region_boundaries_by_event:
            values[name] = self.event_indicators[name].evaluate(self)
        return values

    def detect_event_crossings(
        self, previous: dict[str, float], current: dict[str, float], sign_tolerance: float = 1e-10
    ) -> list[str]:
        """Detect zero-crossings on the active component and on this wrapper.

        Mirrors :meth:`evaluate_event_indicators`. The active sub-component
        reports crossings of its own physics indicators, and this wrapper
        reports crossings of its generated region boundaries.

        Args:
            previous: Indicator values before the step.
            current: Indicator values after the step.
            sign_tolerance: Threshold for zero detection.

        Returns:
            List of indicator names that experienced crossings, without
            duplicates. Empty if neither source has indicators.
        """
        events: list[str] = []
        if self.active_comp.has_state_events:
            events.extend(
                self.active_comp.detect_event_crossings(previous, current, sign_tolerance)
            )
        # Restricted to generated region boundaries for the same reason as
        # ``evaluate_event_indicators``: the others are the active model's.
        for name in super().detect_event_crossings(previous, current, sign_tolerance):
            if name in self._region_boundaries_by_event and name not in events:
                events.append(name)
        return events

    def snapshot_state(self):
        """Capture state snapshot from the active component.

        Delegates to the active sub-component's snapshot mechanism.
        Used for time rollback during event localization.

        Returns:
            Opaque snapshot from the active component.

        Warning:
            The snapshot is only valid for restoration to the same
            active component. Mode switches invalidate snapshots.
        """
        return self.active_comp.snapshot_state()

    def _checkpoint_solver_state(self) -> None:
        """The active child's recursive checkpoint owns backend solver state."""

    def _restore_checkpoint_solver_state(self, snapshot: Any, t: float) -> None:
        """No local solver exists; child checkpoints restore backend state."""

    def _checkpoint_children(self) -> tuple[CoSimComponent, ...]:
        """Checkpoint only the child that can change during an active advance."""
        return (self.active_comp,)

    def _trial_children(self) -> tuple[CoSimComponent, ...]:
        """Propagate trial suppression to every registered model exactly once."""
        unique: dict[int, CoSimComponent] = {}
        for model in self.models.values():
            unique.setdefault(id(model), model)
        return tuple(unique.values())

    def _checkpoint_metadata(self) -> dict[str, Any]:
        """Capture switching identity and transaction-visible wrapper state."""
        return {
            "active_mode": self._active_mode,
            "active_region_index": self.active_region_index,
            "latest_inputs": self._latest_inputs,
            "sync_events": self.sync_events,
            "prev_state": self._prev_state,
            "curr_state": self._curr_state,
            "initializing_regions": self._initializing_regions,
        }

    def _restore_checkpoint_metadata(self, metadata: Any) -> None:
        """Restore metadata captured by :meth:`_checkpoint_metadata`."""
        self._active_mode = metadata["active_mode"]
        self.active_region_index = metadata["active_region_index"]
        self._latest_inputs = metadata["latest_inputs"]
        self.sync_events[:] = metadata["sync_events"]
        self._prev_state = metadata["prev_state"]
        self._curr_state = metadata["curr_state"]
        self._initializing_regions = metadata["initializing_regions"]

    def restore_state(self, snapshot, t) -> None:
        """Restore state snapshot on the active component.

        Delegates to the active sub-component's restore mechanism.
        Used to roll back time during event localization bisection.

        Args:
            snapshot: Opaque snapshot from ``snapshot_state()``.
            t: Time at which the snapshot was taken.

        Warning:
            Must restore to the same component that created the snapshot.
            Do not switch modes between snapshot and restore.
        """
        self.active_comp.restore_state(snapshot, t)

    @property
    def has_state_events(self) -> bool:
        """``True`` if this wrapper or its active model has state events."""
        return bool(self._region_boundaries_by_event) or self.active_comp.has_state_events

    @property
    def self_handled_events(self) -> list[str]:
        """Region events are handled by this wrapper, so it subscribes itself."""
        return list(self._region_boundaries_by_event)

    @property
    def supports_rollback(self) -> bool:
        """``True`` if every reachable region model supports state rollback."""
        if self.switch_regions is not None:
            return all(
                self.models[mode].supports_rollback for mode in set(self.switch_regions.modes)
            )
        return self.active_comp.supports_rollback

    def _handle_events_internal(self, event_names: list[str], t: float) -> None:
        """Handle model events on the active component, then apply any switch.

        Called by the hybrid algorithm once the event time has been localized
        by bisection and the state has been advanced to it. Switching here,
        rather than at the top of the next macro step, is what places the
        transition at the crossing instant instead of on the macro grid.

        The ordering matters. Model events are handled first, on the model
        that produced them, so that the state handed to the incoming model is
        the post-event state.

        Args:
            event_names: List of events that occurred at time ``t``.
            t: Localized time at which the events occurred.
        """
        model_events = [
            name for name in event_names if name not in self._region_boundaries_by_event
        ]
        if model_events:
            self.active_comp.handle_event(model_events, t)

        region_target = self._resolve_region_target(event_names)
        if region_target is not None:
            target_index, _target_mode = region_target
            self._switch_region(target_index, t)

    def get_internal_event_hints(self) -> list[InternalEventInfo]:
        """Retrieve internal event hints from the active component.

        Forwarding is unconditional so that hints reported by the active
        model during a trial step are visible to the hybrid algorithm and
        can short-circuit bisection.

        Returns:
            List of ``InternalEventInfo`` objects from the active component.
        """
        return self.active_comp.get_internal_event_hints()

    # -------------------------------------------------------------------
    # Detect Direct Feedthrough
    # -------------------------------------------------------------------
    def _detect_direct_feedthrough(self):
        """Determine if all models have consistent direct feedthrough.

        Checks the ``direct_feedthrough`` property of all registered
        sub-components. If they differ, raises an error. Otherwise,
        sets this ``MultiComponent``'s ``direct_feedthrough`` property
        accordingly.
        """
        self.direct_feedthrough = None
        for mode_key, comp in self.models.items():
            if comp is None:
                continue
            if self.direct_feedthrough is None:
                self.direct_feedthrough = comp.direct_feedthrough
            elif self.direct_feedthrough != comp.direct_feedthrough:
                raise ValueError(
                    f"{self.name}: Inconsistent direct feedthrough across models. "
                    f"Model '{mode_key}' has direct_feedthrough={comp.direct_feedthrough}, "
                    f"expected {self.direct_feedthrough}."
                )

    # -------------------------------------------------------------------
    # Reset Logic
    # -------------------------------------------------------------------
    def reset(self) -> None:
        """Reset all registered sub-components.

        Calls ``reset()`` on every non-None model in the registry,
        clearing their state and allowing re-initialization. Also
        clears the cached input replay buffer.

        Note:
            Unlike the base class, this resets ALL models, not just
            the active one. This ensures clean state when the
            ``MultiComponent`` is re-initialized.
        """
        super().reset()
        for comp in self.models.values():
            if comp is not None:
                comp.reset()
        self._active_mode = self._initial_mode
        self._latest_inputs = None
        self.active_region_index = None
        self.sync_events.clear()
        self._prev_state = None
        self._curr_state = None
        self._initializing_regions = False
        self._allow_mode_switching = True
