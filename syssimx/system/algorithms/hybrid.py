"""
Hybrid Co-Simulation Algorithm with Event Detection and Handling.

This module provides an implementation of a hybrid co-simulation algorithm
that combines continuous integration with event detection and handling.
The algorithm supports superdense time semantics, event time localization,
and iterative event handling to ensure accurate and consistent simulation
results in the presence of discrete events.

Classes:
    HybridAlgorithm: Implements the hybrid co-simulation algorithm with
        event detection and handling.

Functions:
    _prepare_inputs: Prepares inputs for all generations and solves algebraic loops.
    _detect_crossings: Detects event crossings in a given time interval.
    _locate_event_time: Locates the event time within a given interval using bisection.
    _evaluate_indicators_at: Evaluates event indicators for all event source components at a target
    _evaluate_component_indicators: Evaluates event indicators for a single component at a target time.
    _detect_crossing_between: Detects crossings between two sets of indicator values for all event
    _restore_all_to_left: Restores all components to their state at the left boundary of the interval.
    _handle_events: Handles the specified events at the given time.

Usage:
    The `HybridAlgorithm` class is designed to be used as part of the system
    simulation framework. It extends the Gauss-Seidel algorithm by adding
    support for event detection and handling.

Example:
    .. code-block:: python

        from syssimx.system.algorithms.hybrid import HybridAlgorithm

        algorithm = HybridAlgorithm()
        algorithm.step(system, t, dt)
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from ...core.events import DenseTime, Event, InternalEventInfo
from .base import Algorithm
from .gauss_seidel import GaussSeidelAlgorithm
from .ijcsa import solve_algebraic_scc_ijcsa

if TYPE_CHECKING:
    from ...core.base import CoSimComponent
    from ..system import System

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# Hybrid Co-Simulation Algorithm
# --------------------------------------------------------------------------
class HybridAlgorithm(Algorithm):
    """
    Hybrid co-simulation algorithm with event detection and handling.

    This algorithm combines continuous integration with event detection and
    handling. It supports superdense time semantics, event time localization,
    and iterative event handling to ensure accurate and consistent simulation
    results in the presence of discrete events.

    Attributes:
        name (str): Name of the algorithm.
        tol_value (float): Tolerance for numerical computations.
        max_iter (int): Maximum number of iterations for convergence.
        sign_tolerance (float): Tolerance for detecting sign changes in event indicators.
        tol_time (float): Tolerance for time comparisons.
        event_dedup_tol (float): Tolerance for deduplicating events. Events of
            the same type handled within this time window are treated as
            duplicates and skipped.
        max_microsteps (int): Maximum number of microsteps for event handling.
        gauss_seidel_algorithm (GaussSeidelAlgorithm): Fallback algorithm for
            continuous integration in the absence of events.
        record_internal_steps (bool): If True, records internal steps during
            event handling.
    """

    def __init__(self):
        self.name: str = "Hybrid-Algorithm"
        self.tol_value: float = 1e-6
        self.max_iter: int = 50
        self.sign_tolerance: float = 1e-10
        self.tol_time: float = 1e-8
        self.event_dedup_tol: float = 1e-4
        self.max_microsteps: int = 100
        self.gauss_seidel_algorithm: GaussSeidelAlgorithm = GaussSeidelAlgorithm()
        self.record_internal_steps: bool = False

    # --------------------------------------------------------------------------
    # Global Step Method
    # --------------------------------------------------------------------------
    def step(self, system: System, t: float, dt: float) -> None:
        """
        Perform a hybrid co-simulation step with event detection and handling.

        This method advances the simulation by one macro-step, handling events
        at superdense time points and falling back to the Gauss-Seidel
        algorithm for continuous integration when no events are detected.

        Args:
            system (System): The system to simulate.
            t (float): The current simulation time.
            dt (float): The time step size.

        Raises:
            RuntimeError: If the maximum number of microsteps is reached during
                event handling.
        """
        event_sources = system.event_sources

        t_left = t
        t_right = t + dt
        eps = 1e-12

        # Track all events handled in this macro-step (to avoid duplicates at boundaries)
        # Maps (comp_name, event_name) -> time at which it was last handled
        handled_events_this_step: dict[tuple[str, str], float] = {}

        while t_left < t_right - eps:
            # 1) Prpare inputs: set inputs and resolve algebraic loops
            self._prepare_inputs(system, t_left)

            # 2) Detect crossings (also collects internal event hints)
            snapshots, input_cache, indicators_left, crossings, internal_hints = (
                self._detect_crossings(event_sources, t_left, t_right)
            )

            # 3) If no crossings, do a full step and exit
            if not crossings:
                self.gauss_seidel_algorithm.step(system, t_left, t_right - t_left)
                return

            logger.info("%s", "=" * 80)
            logger.info(
                "Event crossing in [%.6f, %.6f]: %s",
                t_left,
                t_right,
                ", ".join(f"{c}.{e}" for c, e in crossings),
            )
            if internal_hints:
                for comp_name, hints_list in internal_hints.items():
                    logger.debug(
                        "  Internal hints from %s: %s",
                        comp_name,
                        [h.event_name for h in hints_list],
                    )

            # 4) Locate event time (using internal hints if available)
            dense_time, initial_events = self._locate_event_time(
                event_sources,
                snapshots,
                input_cache,
                indicators_left,
                t_left,
                t_right,
                internal_hints,
            )

            logger.info("Event located at t=%.8f", dense_time.t)
            logger.debug(
                "  Events at located time: %s",
                ", ".join(f"{c}.{e}" for c, e in initial_events),
            )

            # 5) Filter out events that were already handled nearby
            new_events = []
            for comp_name, event_name in initial_events:
                event_key = (comp_name, event_name)
                prev_t = handled_events_this_step.get(event_key)
                if prev_t is not None and abs(dense_time.t - prev_t) < self.event_dedup_tol:
                    logger.debug(
                        "  Skipping duplicate: %s.%s (already handled at t=%.8f, "
                        "\u0394t=%.2e < tol=%.2e)",
                        comp_name,
                        event_name,
                        prev_t,
                        abs(dense_time.t - prev_t),
                        self.event_dedup_tol,
                    )
                else:
                    new_events.append((comp_name, event_name))

            initial_events = new_events
            # 6) Step all components to event time
            self.gauss_seidel_algorithm.step(system, t_left, dense_time.t - t_left)

            # 7) Iterative event handling
            all_handled_events = set()
            event_pairs = initial_events
            current_time = dense_time
            while event_pairs and current_time.micro < self.max_microsteps:
                logger.info(
                    "Handling %d event(s) at t=%.8f, micro=%d: %s",
                    len(event_pairs),
                    current_time.t,
                    current_time.micro,
                    ", ".join(f"{c}.{e}" for c, e in event_pairs),
                )

                # a) Record events with microstep and mark as handled
                for comp_name, event_name in event_pairs:
                    system.history.record_event(comp_name, event_name, current_time)
                    all_handled_events.add((comp_name, event_name))
                    handled_events_this_step[(comp_name, event_name)] = current_time.t

                # b) Indicators before handling
                indicators_before_handling = {
                    comp.name: comp.evaluate_event_indicators() for comp in event_sources
                }

                # c) Handle events
                self.handle_events(system, event_pairs, current_time)

                # d) Update inputs and solve algebraic loops
                self._prepare_inputs(system, current_time.t)

                # e) Evaluate indicators after handling
                indicators_after_handling = {
                    comp.name: comp.evaluate_event_indicators() for comp in event_sources
                }

                # f) Detect new events triggered by handlers
                new_events = []
                for comp in event_sources:
                    events = comp.detect_event_crossings(
                        indicators_before_handling[comp.name],
                        indicators_after_handling[comp.name],
                        sign_tolerance=self.sign_tolerance,
                    )
                    for event_name in events:
                        event_pair = (comp.name, event_name)
                        if event_pair not in all_handled_events and event_pair not in new_events:
                            new_events.append(event_pair)
                if new_events:
                    logger.info(
                        "Cascaded events: %s",
                        ", ".join(f"{c}.{e}" for c, e in new_events),
                    )

                # g) Advance microstep if new events detected
                if new_events:
                    event_pairs = new_events
                    current_time = current_time.advance_micro()
                else:
                    break

            if current_time.micro >= self.max_microsteps:
                raise RuntimeError("Maximum number of microsteps reached during event handling.")

            # 8) Prepare for next interval
            self._prepare_inputs(system, dense_time.t)

            # 9) Update left time
            t_left = dense_time.t + self.tol_time
            logger.info("%s", "=" * 80)

    # --------------------------------------------------------------------------
    # Helper - Input Preparation and Algebraic Loop Solving
    # --------------------------------------------------------------------------
    def _prepare_inputs(self, system: System, t: float) -> None:
        """Prepare inputs for all generations and solve algebraic loops.

        This method sets the inputs for all generations in the system and
        resolves any algebraic loops within each generation.

        Args:
            system (System): The system containing the components and connections.
            t (float): The current simulation time.
        """
        for gen in system.execution_order:
            system._set_inputs_for_generation(gen, t)
            gen_set = set(gen)
            for loop in system.algebraic_loops:
                if set(loop).issubset(gen_set):
                    solve_algebraic_scc_ijcsa(system, loop, t)

    # --------------------------------------------------------------------------
    # Event Detection
    # --------------------------------------------------------------------------
    def _detect_crossings(
        self, event_sources: list[CoSimComponent], t_left: float, t_right: float
    ) -> tuple[
        dict[str, Any],
        dict[str, dict[str, Any]],
        dict[str, dict[str, float]],
        list[tuple[str, str]],
        dict[str, list[InternalEventInfo]],
    ]:
        """Detect event crossings in a given time interval.

        This method identifies events that occur within the specified time
        interval by evaluating event indicators and collecting internal hints
        from components with micro-stepping capabilities.

        Args:
            event_sources (list[CoSimComponent]): List of components that can
                generate events.
            t_left (float): Start of the time interval.
            t_right (float): End of the time interval.

        Returns:
            tuple: A tuple containing the following elements:
                - snapshots (dict[str, Any]): State snapshots of components at t_left.
                - input_cache (dict[str, dict[str, Any]]): Cached inputs of components at t_left.
                - indicators_left (dict[str, dict[str, float]]): Event indicator values at t_left.
                - crossings (list[tuple[str, str]]): List of (component name, event name) tuples
                  where crossings were detected.
                - internal_hints (dict[str, list[InternalEventInfo]]): Mapping of component names
                  to lists of InternalEventInfo.
        """
        snapshots: dict[str, Any] = {}
        input_cache: dict[str, dict[str, Any]] = {}
        indicators_left: dict[str, dict[str, float]] = {}
        crossings: list[tuple[str, str]] = []
        internal_hints: dict[str, list[InternalEventInfo]] = {}

        dt = t_right - t_left
        dt = max(0, dt)

        for comp in event_sources:
            # Trial advance: suppress history recording and mode switching.
            with self._trial_step(comp):
                # a) Save the state snapshot, input cache, and indicators at t_left
                snapshots[comp.name] = comp.snapshot_state()
                input_cache[comp.name] = self._capture_inputs(comp)
                indicators_left[comp.name] = comp.evaluate_event_indicators()

                # b) Step to t_right and evaluate indicators at t_right
                comp._do_step_internal(t_left, dt)
                comp._update_output_states()
                indicators_right = comp.evaluate_event_indicators()

                # c) Collect internal event hints and filter to (t_left, t_right]
                raw_hints = comp.get_internal_event_hints()
                filtered_hints = []
                if raw_hints:
                    # Only keep hints that are strictly within the interval
                    for hint in raw_hints:
                        if hint.t_after > t_left + self.tol_time and hint.t_before < t_right:
                            filtered_hints.append(hint)
                            logger.debug(
                                "Internal hint: %s.%s in [%.8f, %.8f]",
                                comp.name,
                                hint.event_name,
                                hint.t_before,
                                hint.t_after,
                            )

                if filtered_hints:
                    internal_hints[comp.name] = filtered_hints

                # d) Detect crossings between left and right
                macro_events = comp.detect_event_crossings(
                    indicators_left[comp.name],
                    indicators_right,
                    sign_tolerance=self.sign_tolerance,
                )

                # e) Combine macro events and micro events (from hints)
                micro_event_names = (
                    [hint.event_name for hint in filtered_hints] if filtered_hints else []
                )
                all_event_names = set(macro_events) | set(micro_event_names)

                # f) Record crossings - iterate over event names, not wrap in list
                for event_name in all_event_names:
                    crossings.append((comp.name, event_name))

                # g) Restore to t_left
                self._restore_with_inputs(
                    comp, snapshots[comp.name], input_cache[comp.name], t_left
                )

        return snapshots, input_cache, indicators_left, crossings, internal_hints

    @staticmethod
    @contextmanager
    def _trial_step(comp: Any):
        """Guard a trial (rolled-back) advance of ``comp``.

        Inside the block the component must not record history and, for
        multi-model components, must not switch its active model: the caller
        restores a snapshot afterwards, and that snapshot is only valid for
        the model that created it. Both flags are restored on exit even if
        the trial advance raises.
        """
        original_switch = getattr(comp, "_allow_mode_switching", None)
        if original_switch is not None:
            comp._allow_mode_switching = False
        original_record = getattr(comp, "_record_history", None)
        if original_record is not None:
            comp._record_history = False
        try:
            yield
        finally:
            if original_switch is not None:
                comp._allow_mode_switching = original_switch
            if original_record is not None:
                comp._record_history = original_record

    def _capture_inputs(self, comp: CoSimComponent) -> dict[str, Any]:
        """Capture the current inputs of the component."""
        inputs: dict[str, Any] = {}
        for name, port in comp.inputs.items():
            value = port.get()
            if value is not None:
                inputs[name] = value
        return inputs

    def _restore_with_inputs(
        self, comp: CoSimComponent, snapshot: Any, inputs: dict[str, Any], t: float
    ) -> None:
        """Restore the component's state from snapshot and set its inputs."""
        comp.restore_state(snapshot, t=t)
        if inputs:
            comp.set_inputs(inputs, t=t)

    # --------------------------------------------------------------------------
    # Event Trigger Time Localization
    # --------------------------------------------------------------------------
    def _locate_event_time(
        self,
        event_sources: list[CoSimComponent],
        snapshots_left: dict[str, Any],
        input_cache: dict[str, dict[str, Any]],
        indicators_left: dict[str, dict[str, float]],
        t_left: float,
        t_right: float,
        internal_hints: dict[str, list[InternalEventInfo]] | None = None,
    ) -> tuple[DenseTime, list[tuple[str, str]]]:
        """Locate the event time within [t_left, t_right] using bisection.

        If internal_hints are provided (from components with internal micro-stepping),
        the algorithm uses these to narrow the search interval before bisection,
        significantly reducing the number of iterations needed.

        Returns the located event time and the list of (component name, event name) tuples.
        """
        logger.debug("Starting bisection for event localization ...")
        # 1) Initialize bisection boundaries
        left = t_left
        right = t_right
        t_left_ref = t_left  # Reference time for current snapshots
        t_event = t_right  # Default event time if not found

        # 2) Collect events from internal hints that fall within the interval
        events_from_hints: list[tuple[str, str]] = []
        if internal_hints:
            for comp_name, hints in internal_hints.items():
                for hint in hints:
                    # Only consider hints within [t_left, t_right]
                    if hint.t_before >= t_left - 1e-12 and hint.t_after <= t_right + 1e-12:
                        events_from_hints.append((comp_name, hint.event_name))

        # 3) Use internal hints to narrow the initial interval
        if internal_hints:
            earliest_hint = self._get_earliest_event_hint(internal_hints, t_left, t_right)
            if earliest_hint:
                # Narrow the search interval based on internal micro-step timing
                hint_left = max(t_left, earliest_hint.t_before)
                hint_right = min(t_right, earliest_hint.t_after)

                logger.debug(
                    "Narrowed interval via hint: [%.6f, %.6f] -> [%.6f, %.6f]",
                    left,
                    right,
                    hint_left,
                    hint_right,
                )

                # Update boundaries
                left = hint_left
                right = hint_right

                # If the hint interval is already precise enough, use it directly
                if right - left <= self.tol_time:
                    t_event = right
                    # Ensure components are at t_left
                    self._restore_all_to_left(event_sources, snapshots_left, input_cache, t_left)
                    # Return events from hints since indicator check may miss them
                    if events_from_hints:
                        return DenseTime(t=t_event, micro=0), events_from_hints
                    # Fallback to indicator-based collection (trial step)
                    for comp in event_sources:
                        with self._trial_step(comp):
                            self._restore_with_inputs(
                                comp, snapshots_left[comp.name], input_cache[comp.name], t_left
                            )
                            comp._do_step_internal(t_left, t_event - t_left)
                            comp._update_output_states()
                    all_events = self._collect_events_at_time(event_sources)
                    self._restore_all_to_left(event_sources, snapshots_left, input_cache, t_left)
                    return DenseTime(
                        t=t_event, micro=0
                    ), all_events if all_events else events_from_hints

        # 4) Indicator values at boundaries
        indicators_left_vals: dict[str, dict[str, float]] = indicators_left

        # 5) If we narrowed with hints, also update left indicators
        if left > t_left:
            indicators_left_vals = self._evaluate_indicators_at(
                event_sources, snapshots_left, input_cache, t_left, left
            )
            t_left_ref = left

        indicators_right_vals = self._evaluate_indicators_at(
            event_sources, snapshots_left, input_cache, t_left, right
        )

        logger.debug("Indicators at left  (t=%.8f): %s", left, indicators_left_vals)
        logger.debug("Indicators at right (t=%.8f): %s", right, indicators_right_vals)

        # 6) Working snapshots - start from t_left_ref (trial advance)
        working_snapshots = {}
        for comp in event_sources:
            with self._trial_step(comp):
                self._restore_with_inputs(
                    comp, snapshots_left[comp.name], input_cache[comp.name], t_left
                )
                if t_left_ref > t_left + 1e-12:
                    comp._do_step_internal(t_left, t_left_ref - t_left)
                    comp._update_output_states()
                working_snapshots[comp.name] = comp.snapshot_state()

        # 7) Bisection loop
        for iteration in range(self.max_iter):
            logger.debug("Bisection iteration %d: interval [%.8f, %.8f]", iteration + 1, left, right)
            # a) Check termination: interval width
            if right - left <= self.tol_time:
                t_event = right
                break

            # b) Bisect the interval
            mid = 0.5 * (left + right)

            # c) Evaluate indicators at midpoint (with frozen inputs from t_left_ref)
            indicators_mid = self._evaluate_indicators_at(
                event_sources, working_snapshots, input_cache, t_left_ref, mid
            )

            # d) Detect crossings in [left, mid]
            events_left_interval = self._detect_crossing_between(
                event_sources, indicators_left_vals, indicators_mid
            )

            # e) Check if we found exact crossing at midpoint
            if len(events_left_interval) == 1:
                comp_name, event_name = events_left_interval[0]
                indicator_value = indicators_mid[comp_name][event_name]
                if abs(indicator_value) <= self.tol_value:
                    # Found exact event time
                    t_event = mid
                    break

            # f) Narrow interval based on where events were detected
            if events_left_interval:
                # Events in [left, mid], narrow to find the earliest
                right = mid
            else:
                # No events in [left, mid], the event must be in [mid, right]
                left = mid
                indicators_left_vals = indicators_mid
                # Update working snapshots
                working_snapshots = {comp.name: comp.snapshot_state() for comp in event_sources}
                t_left_ref = mid
                t_event = right

        # 8) Collect all events at located time
        #    Step all components to t_event and check indicators.
        #    The components are restored to t_left afterwards, so this is
        #    a trial advance.
        for comp in event_sources:
            with self._trial_step(comp):
                self._restore_with_inputs(
                    comp, snapshots_left[comp.name], input_cache[comp.name], t_left
                )
                comp._do_step_internal(t_left, t_event - t_left)
                comp._update_output_states()

        all_events_at_t = self._collect_events_at_time(event_sources)

        # If indicator-based collection missed events, use hint-based events
        if not all_events_at_t and events_from_hints:
            # Filter hints to those near t_event
            all_events_at_t = []
            for comp_name, event_name in events_from_hints:
                if internal_hints and comp_name in internal_hints:
                    for hint in internal_hints[comp_name]:
                        if (
                            hint.event_name == event_name
                            and hint.t_before <= t_event <= hint.t_after + self.tol_time
                        ):
                            all_events_at_t.append((comp_name, event_name))
                            break

        # 9) Restore all components to state at t_left
        self._restore_all_to_left(event_sources, snapshots_left, input_cache, t_left)

        return DenseTime(t=t_event, micro=0), all_events_at_t

    def _get_earliest_event_hint(
        self,
        internal_hints: dict[str, list[InternalEventInfo]],
        t_left: float | None = None,
        t_right: float | None = None,
    ) -> InternalEventInfo | None:
        """Find the earliest event hint across all components.

        Only considers hints that fall within [t_left, t_right] if provided.
        Returns the InternalEventInfo with the smallest t_before value.
        """
        earliest: InternalEventInfo | None = None
        for comp_name, hints in internal_hints.items():
            for hint in hints:
                # Filter hints to current interval
                if t_left is not None and hint.t_after <= t_left + self.tol_time:
                    continue  # Hint is at or before current interval start
                if t_right is not None and hint.t_before >= t_right:
                    continue  # Hint is after current interval

                if earliest is None or hint.t_before < earliest.t_before:
                    earliest = hint
        return earliest

    def _collect_events_at_time(self, event_sources: list[CoSimComponent]) -> list[tuple[str, str]]:
        """Collect all events at the current time based on indicator values."""
        all_events = []
        for comp in event_sources:
            indicators = comp.evaluate_event_indicators()
            for event_name, value in indicators.items():
                logger.debug("Indicator %s.%s = %.4e", comp.name, event_name, value)
                if abs(value) <= self.tol_value:
                    all_events.append((comp.name, event_name))
        return all_events

    # --------------------------------------------------------------------------
    # Event Trigger Time Localization - Helpers
    # --------------------------------------------------------------------------
    def _evaluate_indicators_at(
        self,
        event_sources: list[CoSimComponent],
        snapshots: dict[str, Any],
        input_cache: dict[str, dict[str, Any]],
        t_left: float,
        t_target: float,
    ) -> dict[str, dict[str, float]]:
        """Evaluate event indicators for all event source components at t_target
        starting from snapshots and input caches at t_left.

        Args:
            event_sources (list[CoSimComponent]): List of components that can
                generate events.
            snapshots (dict[str, Any]): State snapshots of components at t_left.
            input_cache (dict[str, dict[str, Any]]): Cached inputs of components at t_left.
            t_left (float): The left endpoint of the interval.
            t_target (float): The target time for event detection.

        Returns:
            dict[str, dict[str, float]]: A dictionary mapping component names to
            dictionaries of event indicator values at t_target.
        """
        indicators: dict[str, dict[str, float]] = {}
        for comp in event_sources:
            indicators[comp.name] = self._evaluate_component_indicators(
                comp, snapshots[comp.name], input_cache[comp.name], t_left, t_target
            )
        return indicators

    def _evaluate_component_indicators(
        self,
        comp: CoSimComponent,
        snapshot: Any,
        inputs: dict[str, Any],
        t_left: float,
        t_target: float,
    ) -> dict[str, float]:
        """Evaluate event indicators for a single component at t_target
        starting from snapshot and input cache at t_left.

        Args:
            comp (CoSimComponent): The component to evaluate indicators for.
            snapshot (Any): The state snapshot of the component at t_left.
            inputs (dict[str, Any]): The inputs to set for the component.
            t_left (float): The left endpoint of the interval.
            t_target (float): The target time for event detection.

        Returns:
            dict[str, float]: A dictionary of event indicator values at t_target.
        """
        with self._trial_step(comp):
            self._restore_with_inputs(comp, snapshot, inputs, t_left)
            comp._do_step_internal(t_left, t_target - t_left)
            comp._update_output_states()
            if self.record_internal_steps:
                comp._record_outputs(t_target)
            return comp.evaluate_event_indicators()

    def _detect_crossing_between(
        self,
        event_sources: list[CoSimComponent],
        indicators_prev: dict[str, dict[str, float]],
        indicators_curr: dict[str, dict[str, float]],
    ) -> list[tuple[str, str]]:
        """Detect crossings between two sets of indicator values for all event source components.

        Returns a list of (component name, event name) tuples where crossings were detected.
        """
        crossings: list[tuple[str, str]] = []
        for comp in event_sources:
            events = comp.detect_event_crossings(
                indicators_prev[comp.name],
                indicators_curr[comp.name],
                sign_tolerance=self.sign_tolerance,
            )
            for event_name in events:
                crossings.append((comp.name, event_name))
        return crossings

    def _restore_all_to_left(
        self,
        event_sources: list[CoSimComponent],
        snapshots_left: dict[str, Any],
        input_cache: dict[str, dict[str, Any]],
        t_left: float,
    ) -> None:
        """Restore all event source components to their state at t_left."""
        for comp in event_sources:
            self._restore_with_inputs(
                comp, snapshots_left[comp.name], input_cache[comp.name], t_left
            )

    # --------------------------------------------------------------------------
    # Event Handling
    # --------------------------------------------------------------------------
    def handle_events(
        self, system: System, event_pairs: list[tuple[str, str]], current_time: DenseTime
    ) -> None:
        """
        Handles the event_pairs that occur at current_time in the given system.
        If multiple events occur simultaneously, checks for conflicts based on event annotations.
        Ensures that the result is indepnedent of the order of event handling when possible.

        Args:
            system (System): The system in which to handle the events.
            event_pairs (list[tuple[str, str]]): The pairs of (component name, event name)
                representing the events to handle.
            current_time (DenseTime): The current time at which the events occur.

        Raises:
            RuntimeError: If non-commutative events are detected that cannot be
                handled simultaneously.
        """
        # 1) Group for each listener component the events to be handled
        events_by_component: dict[str, list[str]] = {
            listener.name: [] for listener in system.event_listeners
        }
        for listener_name in events_by_component.keys():
            for event_pair in event_pairs:
                if listener_name in system._event_targets_by_source.get(event_pair, []):
                    events_by_component.setdefault(listener_name, []).append(event_pair[1])
        logger.debug("Events grouped by listener: %s", events_by_component)

        # 2) Check for conflicts in each component
        for comp_name, event_names in events_by_component.items():
            if len(event_names) > 1:
                comp = system.components[comp_name]
                if not self._check_event_commutativity(comp, event_names):
                    raise RuntimeError(
                        f"Non-commutative events {event_names} on component {comp_name} detected. "
                        f"Cannot handle simultaneously at {current_time}."
                    )

        # 3) Dispatch events
        for comp_name, event_name in event_pairs:
            system.dispatch_event(Event(name=event_name, source=comp_name), current_time.t)

    def _check_event_commutativity(self, comp: CoSimComponent, event_names: list[str]) -> bool:
        """
        Verify that event handlers commute (order of execution does not matter) for the given component.

        Methods:
        1. Check annotations that specify which states/outputs are modified by each event.
        2. Run all permutations and compare results dynamically (requires state rollback).

        Args:
            comp (CoSimComponent): The component to check commutativity for.
            event_names (list[str]): The list of event names to check.

        Returns:
            bool: True if the event handlers commute, False otherwise.
        """
        logger.debug("Checking commutativity for %s on %s", event_names, comp.name)
        # Method 1) Annotation-based check
        if comp.event_commutativity:
            for i, event1 in enumerate(event_names):
                for event2 in event_names[i + 1 :]:
                    if not comp.event_commutativity.get((event1, event2), False):
                        return False
            logger.debug(
                "Commutativity verified (annotations): %s on %s",
                event_names,
                comp.name,
            )
            return True

        # Method 2) Dynamic check via permutations
        logger.debug("Verifying commutativity dynamically for %s on %s", event_names, comp.name)
        return self._verify_event_commutativity_dynamically(comp, event_names)

    def _verify_event_commutativity_dynamically(
        self, comp: CoSimComponent, event_names: list[str]
    ) -> bool:
        """
        Executes all permutations of event handling and checks if the final state is the same.
        This requires the component to support state snapshotting and restoration.

        Args:
            comp (CoSimComponent): The component to verify commutativity for.
            event_names (list[str]): The list of event names to test in permutations.

        Returns:
            bool: True if all permutations result in the same final state, False otherwise.
        """
        from itertools import permutations

        # 1) Save initial state
        initial_snapshot = comp.snapshot_state()
        t = comp.t

        # 2) Iterate over all orderings
        results = []
        for ordering in permutations(event_names):
            # a) Restore initial state
            comp.restore_state(initial_snapshot, t=t)

            # b) Handle events in the specified order
            for event_name in ordering:
                comp._handle_events_internal([event_name], t=t)
                comp._update_output_states()

            # c) Record final state
            final_state = comp.get_state()
            results.append(final_state)

        # 3) Check if all results are identical
        comp.restore_state(initial_snapshot, t=t)  # Restore to initial state
        first_result = results[0]
        if all(self._states_equal(first_result, other) for other in results[1:]):
            logger.debug(
                "Commutativity verified (dynamic): %s on %s",
                event_names,
                comp.name,
            )
            return True
        else:
            logger.warning(
                "Non-commutative events detected: %s on %s",
                event_names,
                comp.name,
            )
            return False

    def _states_equal(self, state1: dict, state2: dict) -> bool:
        """
        Compares two component states for equality.
        This method may need to be customized based on the component's state structure.

        Args:
            state1 (dict): The first state to compare.
            state2 (dict): The second state to compare.

        Returns:
            bool: True if the states are equal, False otherwise.
        """
        if state1.keys() != state2.keys():
            return False
        for key in state1.keys():
            if abs(state1[key] - state2[key]) > self.tol_value:
                return False
        return True
