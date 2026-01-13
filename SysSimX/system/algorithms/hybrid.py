from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Tuple, Any

from .base import Algorithm
from .gauss_seidel import GaussSeidelAlgorithm
from .ijcsa import solve_algebraic_scc_ijcsa
from ...core.events import Event, DenseTime

if TYPE_CHECKING:
    from ..system import System
    from ...core.base import CoSimComponent

#--------------------------------------------------------------------------
# Hybrid Co-Simulation Algorithm
#--------------------------------------------------------------------------
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
        self.tol_value: float = 1e-8
        self.max_iter: int = 50
        self.sign_tolerance: float = 1e-10
        self.tol_time: float = 1e-10
        self.max_microsteps: int = 100
        self.gauss_seidel_algorithm: GaussSeidelAlgorithm = GaussSeidelAlgorithm()
        self.verbose: bool = True

    #--------------------------------------------------------------------------
    # Global Step Method
    #--------------------------------------------------------------------------
    def step(self, system: "System", t: float, dt: float) -> None:
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
        if self.verbose: print(f"Time: {t:.4f} s", end='\r')

        while t_left < t_right - eps:
            # 1) Prpare inputs: set inputs and resolve algebraic loops
            self._prepare_inputs(system, t_left)

            # 2) Detect crossings
            snapshots, input_cache, indicators_left, crossings = self._detect_crossings(
                event_sources, t_left, t_right
            )

            # 3) If no crossings, do a full step and exit
            if not crossings:
                self.gauss_seidel_algorithm.step(system, t_left, t_right - t_left)
                return
            
            if self.verbose:
                print(f"\n{80*'='}")
                print(f"Events detected in interval [{t_left:.8f}, {t_right:.8f}]")
                print(f"Events: {crossings}")

            # 4) Locate event time
            dense_time, initial_events = self._locate_event_time(
                event_sources, snapshots, input_cache, indicators_left, t_left, t_right,
            )
            
            if self.verbose:
                # print(f"\n{80*'='}")
                # print(f"Events detected in interval [{t_left:.8f}, {t_right:.8f}]")
                # print(f"Events: {initial_events}")
                print(f"Located at t={dense_time}")
                
            # 5) Step all components to event time
            self.gauss_seidel_algorithm.step(system, t_left, dense_time.t - t_left)

            # 6) Iterative event handling
            all_handled_events = set()
            event_pairs = initial_events
            current_time = dense_time
            while event_pairs and current_time.micro < self.max_microsteps:
                if self.verbose:
                    print(f"\nHandling events at {current_time}: {event_pairs}")
                # a) Record events with microstep
                for comp_name, event_name in event_pairs:
                    system.history.record_event(comp_name, event_name, current_time)

                # b) Indicators before handling
                indicators_before_handling = {
                    comp.name: comp.evaluate_event_indicators()
                    for comp in event_sources
                }
                
                # c) Handle events
                self.handle_events(system, event_pairs, current_time)

                # d) Update inputs and solve algebraic loops
                self._prepare_inputs(system, current_time.t)

                # e) Evaluate indicators after handling
                indicators_after_handling = {
                    comp.name: comp.evaluate_event_indicators()
                    for comp in event_sources
                }

                # f) Detect new events triggered by handlers
                new_events = []
                for comp in event_sources:
                    events = comp.detect_event_crossing(
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

            # 7) Prepare for next interval
            self._prepare_inputs(system, dense_time)

            # 8) Update left time
            t_left = dense_time.t
            if self.verbose:
                print(f"{80*'='}\n")

    #--------------------------------------------------------------------------
    # Helper - Input Preparation and Algebraic Loop Solving
    #--------------------------------------------------------------------------
    def _prepare_inputs(self, system: "System", t: float) -> None:
        """
        Set inputs for all generations and solve algebraic loops.
        """
        for gen in system.execution_order:
            system._set_inputs_for_generation(gen, t)
            gen_set = set(gen)
            for loop in system.algebraic_loops:
                if set(loop).issubset(gen_set):
                    solve_algebraic_scc_ijcsa(system, loop, t)

    #--------------------------------------------------------------------------
    # Event Detection
    #--------------------------------------------------------------------------
    def _detect_crossings(self, event_sources: List["CoSimComponent"],
                          t_left: float, t_right: float) -> Tuple[Dict[str, Any],              # snapshots
                                                                  Dict[str, Dict[str, Any]],   # input_cache
                                                                  Dict[str, Dict[str, float]], # indicators_left
                                                                  List[Tuple[str, str]]]:      # crossings
        """
        Detect event crossings in the interval [t_left, t_right] for the given event source components.
        
        Returns:
            
            - snapshots: state snapshots of components at t_left
            - input_cache: cached inputs of components at t_left
            - indicators_left: event indicator values at t_left
            - crossings: list of (component name, event name) tuples where crossings were detected
        """
        snapshots: Dict[str, Any] = {}
        input_cache: Dict[str, Dict[str, Any]] = {}
        indicators_left: Dict[str, Dict[str, float]] = {}
        crossings: List[Tuple[str, str]] = []

        dt = t_right - t_left
        dt = max(0, dt) # Ensure non-negative step size
        for comp in event_sources:
            # a) Disable mode switching for trial step
            if hasattr(comp, '_allow_mode_switching'):
                original_flag = comp._allow_mode_switching
                comp._allow_mode_switching = False
            try:
                # b) Save the state snapshot, input cache, and indicators at t_left
                snapshots[comp.name] = comp.snapshot_state()
                input_cache[comp.name] = self._capture_inputs(comp)
                indicators_left[comp.name] = comp.evaluate_event_indicators()
                
                # c) Step to t_right and evaluate indicators at t_right
                internal_events = comp._do_step_internal(t_left, dt)
                if internal_events:
                    print(f"Internal events detected in component {comp.name}: {internal_events}")
                comp._update_output_states()
                indicators_right = comp.evaluate_event_indicators()

                # d) Detect crossings between left and right
                events = comp.detect_event_crossing(
                    indicators_left[comp.name],
                    indicators_right,
                    sign_tolerance=self.sign_tolerance,
                )

                # e) Record crossings
                for event_name in [events+internal_events]:
                    crossings.append((comp.name, event_name))

                # f) Restore to t_left
                self._restore_with_inputs(comp, snapshots[comp.name], input_cache[comp.name], t_left)
            
            finally:
                # g) Re-enable mode switching
                if hasattr(comp, '_allow_mode_switching'):
                    comp._allow_mode_switching = original_flag

        return snapshots, input_cache, indicators_left, crossings
    
    def _capture_inputs(self, comp: "CoSimComponent") -> Dict[str, Any]:
        """
        Capture the current inputs of the component.
        """
        inputs: Dict[str, Any] = {}
        for name, port in comp.inputs.items():
            value = port.get()
            if value is not None:
                inputs[name] = value
        return inputs
    
    def _restore_with_inputs(self,
                             comp: "CoSimComponent",
                             snapshot: Any,
                             inputs: Dict[str, Any],
                             t: float) -> None:
        """
        Restore the component's state from snapshot and set its inputs.
        """
        try:
            comp.restore_state(snapshot, t=t)
        except TypeError:
            comp.restore_state(snapshot)
        if inputs:
            comp.set_inputs(inputs, t=t)

    #--------------------------------------------------------------------------
    # Event Trigger Time Localization
    #--------------------------------------------------------------------------
    def _locate_event_time(self,
                           event_sources: List["CoSimComponent"],
                           snapshots_left: Dict[str, Any],
                           input_cache: Dict[str, Dict[str, Any]],
                           indicators_left: Dict[str, Dict[str, float]],
                           t_left: float, t_right: float) -> Tuple[DenseTime, List[Tuple[str, str]]]:
        """
        Locate the event time within [t_left, t_right] using bisection.
        Returns the located event time and the list of (component name, event name) tuples.
        """
        # 1) Initialize bisection boundaries
        left = t_left
        right = t_right
        t_left_ref = t_left # Reference time for current snapshots
        t_event = t_right   # Default event time if not found

        # 2) Indicator values at boundaries
        indicators_left: Dict[str, Dict[str, float]] = indicators_left
        indicators_right = self._evaluate_indicators_at(event_sources,
                                                           snapshots_left,
                                                           input_cache,
                                                           t_left, t_right)
        
        # 3) Working snapshots
        working_snapshots = snapshots_left.copy()

        # 4) Bisection loop
        for iteration in range(self.max_iter):
            # 1) Check termination: interval width
            if right - left <= self.tol_time:
                t_event = right
                break

            # 2) Bisect the interval
            mid = 0.5 * (left + right)

            # 3) Evaluate indicators at midpoint (with frozen inputs from t_left_ref)
            indicators_mid = self._evaluate_indicators_at(
                event_sources, working_snapshots, input_cache, t_left_ref, mid)
            
            # 4) Detect crossings in [left, mid] and [mid, right]
            events_left = self._detect_crossing_between(
                event_sources, indicators_left, indicators_mid
            )
            events_right = self._detect_crossing_between(
                event_sources, indicators_mid, indicators_right
            )

            # 5) Narrow interval based on where events were detected
            if len(events_left) == 1:
                comp_name, event_name = events_left[0]
                indicator_value = indicators_mid[comp_name][event_name]
                if abs(indicator_value) <= self.tol_value:
                    # Found exact event time
                    t_event = mid
                    break
            if events_left:
                # Multiple events in [left, mid], narrow to find the earliest
                right = mid
                indicators_right = indicators_mid
            else:
                # No events in [left, mid], the event must be in [mid, right]
                left = mid
                indicators_left = indicators_mid
                working_snapshots = {comp.name: comp.snapshot_state() for comp in event_sources}
                t_left_ref = mid
                t_event = right

        # 6) Collect all events at located time
        all_events_at_t = []
        for comp in event_sources:
            indicators = comp.evaluate_event_indicators()
            for event_name, value in indicators.items():
                if abs(value) <= self.tol_value:
                    all_events_at_t.append((comp.name, event_name))

        # 7) Restore all components to state at t_left
        self._restore_all_to_left(event_sources, snapshots_left, input_cache, t_left)

        return DenseTime(t=t_event, micro=0), all_events_at_t

    #--------------------------------------------------------------------------
    # Event Trigger Time Localization - Helpers
    #--------------------------------------------------------------------------
    def _evaluate_indicators_at(self,
                                event_sources: List["CoSimComponent"],
                                snapshots: Dict[str, Any],
                                input_cache: Dict[str, Dict[str, Any]],
                                t_left: float, t_target: float) -> Dict[str, Dict[str, float]]:
        """
        Evaluate event indicators for all event source components at t_target
        starting from snapshots and input caches at t_left.
        """
        indicators: Dict[str, Dict[str, float]] = {}
        for comp in event_sources:
            indicators[comp.name] = self._evaluate_component_indicators(
                comp, snapshots[comp.name], input_cache[comp.name], t_left, t_target
            )
        return indicators

    def _evaluate_component_indicators(self,
                                       comp: "CoSimComponent",
                                       snapshot: Any,
                                       inputs: Dict[str, Any],
                                       t_left: float, t_target: float) -> Dict[str, float]:
        """
        Evaluate event indicators for a single component at t_target
        starting from snapshot and input cache at t_left.
        """
        if hasattr(comp, '_allow_mode_switching'):
            original_flag = comp._allow_mode_switching
            comp._allow_mode_switching = False
        try:
            self._restore_with_inputs(comp, snapshot, inputs, t_left)
            comp._do_step_internal(t_left, t_target - t_left)
            comp._update_output_states()
            if self.verbose:
                comp._record_outputs(t_target)
            return comp.evaluate_event_indicators()
        finally:
            if hasattr(comp, '_allow_mode_switching'):
                comp._allow_mode_switching = original_flag


    def _detect_crossing_between(self,
                                 event_sources: List["CoSimComponent"],
                                 indicators_prev: Dict[str, Dict[str, float]],
                                 indicators_curr: Dict[str, Dict[str, float]]) -> List[Tuple[str, str]]:
        """
        Detect crossings between two sets of indicator values for all event source components.
        
        Returns a list of (component name, event name) tuples where crossings were detected.
        """
        crossings: List[Tuple[str, str]] = []
        for comp in event_sources:
            events = comp.detect_event_crossing(
                indicators_prev[comp.name],
                indicators_curr[comp.name],
                sign_tolerance=self.sign_tolerance,
            )
            for event_name in events:
                crossings.append((comp.name, event_name))
        return crossings
    
    def _restore_all_to_left(self,
                             event_sources: List["CoSimComponent"],
                             snapshots_left: Dict[str, Any],
                             input_cache: Dict[str, Dict[str, Any]],
                             t_left: float) -> None:
        """
        Restore all event source components to their state at t_left.
        """
        for comp in event_sources:
            self._restore_with_inputs(
                comp,
                snapshots_left[comp.name],
                input_cache[comp.name],
                t_left
            )
    #--------------------------------------------------------------------------
    # Event Handling
    #--------------------------------------------------------------------------
    def handle_events(self,
                      system: "System",
                      event_pairs: List[Tuple[str, str]],
                      current_time: DenseTime) -> None:
        """
        Handles the event_pairs that occur at current_time in the given system.
        If multiple events occur simultaneously, checks for conflicts based on event annotations.
        Ensures that the result is indepnedent of the order of event handling when possible.
        """
        # 1) Group for each listener component the events to be handled
        events_by_component: Dict[str, List[str]] = {listener.name: [] for listener in system.event_listeners}
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
                        f"Cannot handle simultaneously at {current_time}.")

        # 3) Dispatch events
        for comp_name, event_name in event_pairs:
            system.dispatch_event(Event(name=event_name, source=comp_name), current_time.t)

    def _check_event_commutativity(self,
                                    comp: "CoSimComponent",
                                    event_names: List[str]) -> bool:
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
                    for event2 in event_names[i+1:]:
                        if not comp.event_commutativity.get((event1, event2), False):
                            return False
                if self.verbose:
                    print(f"Event handlers {event_names} on component {comp.name} verified as commutative via annotations.")
                return True

            # Method 2) Dynamic check via permutations
            print('Verifying dynamically ...')
            return self._verify_event_commutativity_dynamically(comp, event_names)

    def _verify_event_commutativity_dynamically(self,
                                                comp: "CoSimComponent",
                                                event_names: List[str]) -> bool:
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
                print(f"Event handlers {event_names} on component {comp.name} verified as commutative via dynamic check.")
            return True
        else:
            if self.verbose:
                print(f"Event handlers {event_names} on component {comp.name} are non-commutative (dynamic check).")
            return False

    def _states_equal(self, state1: Dict, state2: Dict) -> bool:
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