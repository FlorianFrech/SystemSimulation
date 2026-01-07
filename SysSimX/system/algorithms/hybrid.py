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
    Hybrid co-simulation algorithm which is using a Jacobi approach for event detection and localization.
    A Gauss-Seidel approach is used when no events are detected, and for stepping all components to the event time.
    Algebraic loops are solved using the IJCSA method before stepping and after handling events.
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

            # 4) Locate event time
            dense_time, initial_events = self._locate_event_time(
                event_sources, snapshots, input_cache, indicators_left, t_left, t_right,
            )
            
            if self.verbose:
                print(f"\n{80*'='}")
                print(f"Events detected in interval [{t_left:.8f}, {t_right:.8f}]")
                print(f"Events: {initial_events}")
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
                
                # c) Dispatch events
                for comp_name, event_name in event_pairs:
                    system.dispatch_event(Event(name=event_name, source=comp_name), current_time.t)
                    all_handled_events.add((comp_name, event_name))

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
                        indicators_left[comp.name],
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
            # a) Save the state snapshot, input cache, and indicators at t_left
            snapshots[comp.name] = comp.snapshot_state()
            input_cache[comp.name] = self._capture_inputs(comp)
            indicators_left[comp.name] = comp.evaluate_event_indicators()
            
            # b) Step to t_right and evaluate indicators at t_right
            comp._do_step_internal(t_left, dt)
            comp._update_output_states()
            indicators_right = comp.evaluate_event_indicators()

            # c) Detect crossings between left and right
            events = comp.detect_event_crossing(
                indicators_left[comp.name],
                indicators_right,
                sign_tolerance=self.sign_tolerance,
            )

            # d) Record crossings
            for event_name in events:
                crossings.append((comp.name, event_name))

            # e) Restore to t_left
            self._restore_with_inputs(comp, snapshots[comp.name], input_cache[comp.name], t_left)

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
        self._restore_with_inputs(comp, snapshot, inputs, t_left)
        comp._do_step_internal(t_left, t_target - t_left)
        comp._update_output_states()
        if self.verbose:
            comp._record_outputs(t_target)
        return comp.evaluate_event_indicators()


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