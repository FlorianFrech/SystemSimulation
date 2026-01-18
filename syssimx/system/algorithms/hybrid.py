from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np

from ...core.events import DenseTime, Event, InternalEventInfo
from .base import Algorithm
from .gauss_seidel import GaussSeidelAlgorithm
from .ijcsa import solve_algebraic_scc_ijcsa

if TYPE_CHECKING:
    from ...core.base import CoSimComponent
    from ..system import System


# --------------------------------------------------------------------------
# Hybrid Co-Simulation Algorithm
# --------------------------------------------------------------------------
class HybridAlgorithm(Algorithm):
    """
    Hybrid co-simulation algorithm which supports
        - event detection via evaluation of event indicators
        - event time localization using bisection
        - iterative event handling at superdense time points
        - checking for commutativity of event handlers to ensure consistent results

    In absence of events, falls back to Gauss-Seidel algorithm for continuous integration.
    """

    def __init__(self):
        self.name: str = "Hybrid-Algorithm"
        self.tol_value: float = 1e-6
        self.max_iter: int = 50
        self.sign_tolerance: float = 1e-10
        self.tol_time: float = 1e-6
        self.max_microsteps: int = 100
        self.gauss_seidel_algorithm: GaussSeidelAlgorithm = GaussSeidelAlgorithm()
        self.verbose: bool = True
        self.record_internal_steps: bool = False

    # --------------------------------------------------------------------------
    # Global Step Method
    # --------------------------------------------------------------------------
    def step(self, system: System, t: float, dt: float) -> None:
        """
        Hybrid co-simulation step with superdense time support.

        Event Handling:
        ---------------
        When events are detected at time t_event:
        1. All components step to t_event (real time)
        2. Events handled iteratively at microsteps (t_event, 0), (t_event, 1), ...
        3. Loop continues until no new events triggered or max_microsteps reached

        Microstep Semantics:
        --------------------
        - (t, 0): Initial event from zero-crossing detection
        - (t, 1): Events triggered by handlers at (t, 0)
        - (t, n): Events triggered by handlers at (t, n-1)

        Causality: Events at (t, n) can only affect components at (t, n+1) or later.
        """
        event_sources = system.event_sources

        t_left = t
        t_right = t + dt
        eps = 1e-12
        if self.verbose:
            print(f"Time: {t:.4f} s", end="\r")

        # Track all events handled in this macro-step (to avoid duplicates at boundaries)
        handled_events_this_step: set[tuple[str, str, float]] = set()

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

            if self.verbose:
                print(f"\n{80 * '='}")
                print(f"Events detected in interval [{t_left:.8f}, {t_right:.8f}]")
                print(f"Crossings: {crossings}")
                if internal_hints:
                    print(
                        f"Internal hints: {[(c, [h.event_name for h in hs]) for c, hs in internal_hints.items()]}"
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

            if self.verbose:
                print(f"Initial events to handle: {initial_events}")
                print(f"Located at t={dense_time}")

            # 5) Filter out events that were already handled at this time
            t_event_rounded = np.round(dense_time.t, decimals=6)
            new_events = []
            for comp_name, event_name in initial_events:
                event_key = (comp_name, event_name, t_event_rounded)
                if event_key not in handled_events_this_step:
                    new_events.append((comp_name, event_name))
                elif self.verbose:
                    print(
                        f"  Skipping already-handled event: {comp_name}.{event_name} at t≈{t_event_rounded:.8f}"
                    )

            initial_events = new_events
            if self.verbose:
                print(f"Events to handle at t={dense_time}: {initial_events}")
            # 6) Step all components to event time
            self.gauss_seidel_algorithm.step(system, t_left, dense_time.t - t_left)

            # 7) Iterative event handling
            all_handled_events = set()
            event_pairs = initial_events
            current_time = dense_time
            while event_pairs and current_time.micro < self.max_microsteps:
                if self.verbose:
                    print(f"Already handled events: {handled_events_this_step}")
                    print(f"\nHandling events at {current_time}: {event_pairs}")

                # a) Record events with microstep and mark as handled
                for comp_name, event_name in event_pairs:
                    system.history.record_event(comp_name, event_name, current_time)
                    all_handled_events.add((comp_name, event_name))
                    event_key = (comp_name, event_name, t_event_rounded)
                    handled_events_this_step.add(event_key)

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
                if new_events and self.verbose:
                    print(f"\nNew events detected after handling: {new_events}")

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
            if self.verbose:
                print(f"{80 * '='}\n")

    # --------------------------------------------------------------------------
    # Helper - Input Preparation and Algebraic Loop Solving
    # --------------------------------------------------------------------------
    def _prepare_inputs(self, system: System, t: float) -> None:
        """
        Set inputs for all generations and solve algebraic loops.
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
        dict[str, Any],  # snapshots
        dict[str, dict[str, Any]],  # input_cache
        dict[str, dict[str, float]],  # indicators_left
        list[tuple[str, str]],  # crossings
        dict[str, list[InternalEventInfo]],
    ]:  # internal_hints
        """
        Detect event crossings in the interval [t_left, t_right] for the given event source components.

        Returns:
            - snapshots: state snapshots of components at t_left
            - input_cache: cached inputs of components at t_left
            - indicators_left: event indicator values at t_left
            - crossings: list of (component name, event name) tuples where crossings were detected
            - internal_hints: dict mapping component names to lists of InternalEventInfo
        """
        snapshots: dict[str, Any] = {}
        input_cache: dict[str, dict[str, Any]] = {}
        indicators_left: dict[str, dict[str, float]] = {}
        crossings: list[tuple[str, str]] = []
        internal_hints: dict[str, list[InternalEventInfo]] = {}

        dt = t_right - t_left
        dt = max(0, dt)

        for comp in event_sources:
            # a) Disable mode switching for trial step
            if hasattr(comp, "_allow_mode_switching"):
                original_flag = comp._allow_mode_switching
                comp._allow_mode_switching = False
            try:
                # b) Save the state snapshot, input cache, and indicators at t_left
                snapshots[comp.name] = comp.snapshot_state()
                input_cache[comp.name] = self._capture_inputs(comp)
                indicators_left[comp.name] = comp.evaluate_event_indicators()

                # c) Step to t_right and evaluate indicators at t_right
                comp._do_step_internal(t_left, dt)
                comp._update_output_states()
                indicators_right = comp.evaluate_event_indicators()

                # d) Collect internal event hints and filter to (t_left, t_right]
                raw_hints = comp.get_internal_event_hints()
                filtered_hints = []
                if raw_hints:
                    # Only keep hints that are strictly within the interval
                    for hint in raw_hints:
                        if hint.t_after > t_left + self.tol_time and hint.t_before < t_right:
                            filtered_hints.append(hint)
                            if self.verbose:
                                print(
                                    f"  Internal hint from {comp.name}: {hint.event_name} "
                                    f"in [{hint.t_before:.8f}, {hint.t_after:.8f}]"
                                )

                if filtered_hints:
                    internal_hints[comp.name] = filtered_hints

                # e) Detect crossings between left and right
                macro_events = comp.detect_event_crossings(
                    indicators_left[comp.name],
                    indicators_right,
                    sign_tolerance=self.sign_tolerance,
                )

                # f) Combine macro events and micro events (from hints)
                micro_event_names = (
                    [hint.event_name for hint in filtered_hints] if filtered_hints else []
                )
                all_event_names = set(macro_events) | set(micro_event_names)

                # g) Record crossings - iterate over event names, not wrap in list
                for event_name in all_event_names:
                    crossings.append((comp.name, event_name))

                # h) Restore to t_left
                self._restore_with_inputs(
                    comp, snapshots[comp.name], input_cache[comp.name], t_left
                )

            finally:
                # i) Re-enable mode switching
                if hasattr(comp, "_allow_mode_switching"):
                    comp._allow_mode_switching = original_flag

        return snapshots, input_cache, indicators_left, crossings, internal_hints

    def _capture_inputs(self, comp: CoSimComponent) -> dict[str, Any]:
        """
        Capture the current inputs of the component.
        """
        inputs: dict[str, Any] = {}
        for name, port in comp.inputs.items():
            value = port.get()
            if value is not None:
                inputs[name] = value
        return inputs

    def _restore_with_inputs(
        self, comp: CoSimComponent, snapshot: Any, inputs: dict[str, Any], t: float
    ) -> None:
        """
        Restore the component's state from snapshot and set its inputs.
        """
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
        """
        Locate the event time within [t_left, t_right] using bisection.

        If internal_hints are provided (from components with internal micro-stepping),
        the algorithm uses these to narrow the search interval before bisection,
        significantly reducing the number of iterations needed.

        Returns the located event time and the list of (component name, event name) tuples.
        """
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

                if self.verbose:
                    print(
                        f"  Using internal hint to narrow interval: "
                        f"[{left:.8f}, {right:.8f}] -> [{hint_left:.8f}, {hint_right:.8f}]"
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
                    # Fallback to indicator-based collection
                    for comp in event_sources:
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

        # 6) Working snapshots - start from t_left_ref
        working_snapshots = {}
        for comp in event_sources:
            self._restore_with_inputs(
                comp, snapshots_left[comp.name], input_cache[comp.name], t_left
            )
            if t_left_ref > t_left + 1e-12:
                comp._do_step_internal(t_left, t_left_ref - t_left)
                comp._update_output_states()
            working_snapshots[comp.name] = comp.snapshot_state()

        # 7) Bisection loop
        for iteration in range(self.max_iter):
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
        #    Step all components to t_event and check indicators
        for comp in event_sources:
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
        """
        Find the earliest event hint across all components.

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
        """
        Collect all events at the current time based on indicator values.
        """
        all_events = []
        for comp in event_sources:
            indicators = comp.evaluate_event_indicators()
            for event_name, value in indicators.items():
                if self.verbose:
                    print(f"  Indicator for {comp.name}.{event_name} = {value:.8e}")
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
        """
        Evaluate event indicators for all event source components at t_target
        starting from snapshots and input caches at t_left.
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
        """
        Evaluate event indicators for a single component at t_target
        starting from snapshot and input cache at t_left.
        """
        if hasattr(comp, "_allow_mode_switching"):
            original_flag = comp._allow_mode_switching
            comp._allow_mode_switching = False
        try:
            self._restore_with_inputs(comp, snapshot, inputs, t_left)
            comp._do_step_internal(t_left, t_target - t_left)
            comp._update_output_states()
            if self.record_internal_steps:
                comp._record_outputs(t_target)
            return comp.evaluate_event_indicators()
        finally:
            if hasattr(comp, "_allow_mode_switching"):
                comp._allow_mode_switching = original_flag

    def _detect_crossing_between(
        self,
        event_sources: list[CoSimComponent],
        indicators_prev: dict[str, dict[str, float]],
        indicators_curr: dict[str, dict[str, float]],
    ) -> list[tuple[str, str]]:
        """
        Detect crossings between two sets of indicator values for all event source components.

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
        """
        Restore all event source components to their state at t_left.
        """
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
        """
        # 1) Group for each listener component the events to be handled
        events_by_component: dict[str, list[str]] = {
            listener.name: [] for listener in system.event_listeners
        }
        for listener_name in events_by_component.keys():
            for event_pair in event_pairs:
                if listener_name in system._event_targets_by_source.get(event_pair, []):
                    events_by_component.setdefault(listener_name, []).append(event_pair[1])
        if self.verbose:
            print(f"\nEvents grouped by component for handling: {events_by_component}")

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
        """
        if self.verbose:
            print(f"\nChecking commutativity for events {event_names} on component {comp.name}...")
        # Method 1) Annotation-based check
        if comp.event_commutativity:
            for i, event1 in enumerate(event_names):
                for event2 in event_names[i + 1 :]:
                    if not comp.event_commutativity.get((event1, event2), False):
                        return False
            if self.verbose:
                print(
                    f"Event handlers {event_names} on component {comp.name} verified as commutative via annotations."
                )
            return True

        # Method 2) Dynamic check via permutations
        print("Verifying dynamically ...")
        return self._verify_event_commutativity_dynamically(comp, event_names)

    def _verify_event_commutativity_dynamically(
        self, comp: CoSimComponent, event_names: list[str]
    ) -> bool:
        """
        Executes all permutations of event handling and checks if the final state is the same.
        This requires the component to support state snapshotting and restoration.
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
            if self.verbose:
                print(
                    f"Event handlers {event_names} on component {comp.name} verified as commutative via dynamic check."
                )
            return True
        else:
            if self.verbose:
                print(
                    f"Event handlers {event_names} on component {comp.name} are non-commutative (dynamic check)."
                )
            return False

    def _states_equal(self, state1: dict, state2: dict) -> bool:
        """
        Compares two component states for equality.
        This method may need to be customized based on the component's state structure.
        """
        if state1.keys() != state2.keys():
            return False
        for key in state1.keys():
            if abs(state1[key] - state2[key]) > self.tol_value:
                return False
        return True
