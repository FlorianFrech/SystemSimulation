from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Tuple, Any

from .base import Algorithm
from .ijcsa import solve_algebraic_scc_ijcsa
from ...core.events import Event

if TYPE_CHECKING:
    from ..system import System
    from ...core.base import CoSimComponent


@dataclass
class HybridJacobiAlgorithm(Algorithm):
    """
    Hybrid Jacobi algorithm with frozen inputs during a macro step.
    """
    name: str = "Hybrid-Jacobi"
    tol_value: float = 1e-8
    max_iter: int = 50
    sign_tolerance: float = 1e-10
    tol_time: float = 1e-10

    def step(self, system: "System", t: float, dt: float) -> None:
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
                self._step_all(system, t_left, t_right - t_left)
                return

            # 4) Locate event time
            t_event, event_pairs = self._locate_event_time(
                event_sources,
                snapshots,
                input_cache,
                indicators_left,
                t_left,
                t_right,
            )
            for comp_name, event_name in event_pairs:
                system.history.record_event(comp_name, event_name, t_event)

            print(f"\n{'='*60}")
            print(f"Event(s) detected in interval [{t_left:.8f}, {t_right:.8f}]")
            print(f"Located at t={t_event:.8f}")
            print(f"Events: {event_pairs}")
            print(f"{'='*60}\n")

            # 5) Step to event time
            self._step_all(system, t_left, t_event - t_left)

            # 6) Dispatch events: components handle events internally
            for comp_name, event_name in event_pairs:
                system.dispatch_event(Event(name=event_name, source=comp_name), t_event)

            # 7) Prepare for next interval
            self._prepare_inputs(system, t_event)

            # 8) Update left time
            t_left = t_event

    def _prepare_inputs(self, system: "System", t: float) -> None:
        for gen in system.execution_order:
            system._set_inputs_for_generation(gen, t)
            gen_set = set(gen)
            for loop in system.algebraic_loops:
                if set(loop).issubset(gen_set):
                    solve_algebraic_scc_ijcsa(system, loop, t)

    def _step_all(self, system: "System", t: float, dt: float) -> None:
        for gen in system.execution_order:
            for comp_name in gen:
                system.components[comp_name].do_step(t, dt)

    def _jacobi_step(self, system: "System", t: float, dt: float) -> None:
        self._prepare_inputs(system, t)
        self._step_all(system, t, dt)

    def _detect_crossings(
        self,
        event_sources: List["CoSimComponent"],
        t_left: float,
        t_right: float,
    ) -> Tuple[
        Dict[str, Any],
        Dict[str, Dict[str, Any]],
        Dict[str, Dict[str, float]],
        List[Tuple[str, str]],
    ]:
        snapshots: Dict[str, Any] = {}
        input_cache: Dict[str, Dict[str, Any]] = {}
        indicators_left: Dict[str, Dict[str, float]] = {}
        crossings: List[Tuple[str, str]] = []

        dt = t_right - t_left
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

    def _locate_event_time(
        self,
        event_sources: List["CoSimComponent"],
        snapshots: Dict[str, Any],
        input_cache: Dict[str, Dict[str, Any]],
        indicators_left: Dict[str, Dict[str, float]],
        t_left: float,
        t_right: float,
    ) -> Tuple[float, List[Tuple[str, str]]]:
        left = t_left
        right = t_right
        indicators_at_left: Dict[str, Dict[str, float]] = indicators_left
        indicators_at_right = self._evaluate_indicators_at(
            event_sources, snapshots, input_cache, t_left, t_right
        )
        indicators_mid: Dict[str, Dict[str, float]] = {}
        last_events: List[Tuple[str, str]] = []

        for _ in range(self.max_iter):
            # 1) Check termination: interval is small enough
            if right - left <= self.tol_time:
                break

            # 2) Bisect the interval
            mid = 0.5 * (left + right)
            indicators_mid = {}
            events_left_to_mid: List[Tuple[str, str]] = []
            events_mid_to_right: List[Tuple[str, str]] = []

            # 3) Iterate over event sources
            for comp in event_sources:
                # a) Evaluate indicators at mid with frozen inputs
                indicators_mid[comp.name] = self._evaluate_component_indicators(
                    comp, snapshots[comp.name], input_cache[comp.name], t_left, mid
                )

                # b) Detect crossings between left and mid
                events = comp.detect_event_crossing(
                    indicators_at_left[comp.name],
                    indicators_mid[comp.name],
                    sign_tolerance=self.sign_tolerance,
                )
                for event_name in events:
                    events_left_to_mid.append((comp.name, event_name))

                # c) Detect crossings between mid and right
                events = comp.detect_event_crossing(
                    indicators_mid[comp.name],
                    indicators_at_right[comp.name],
                    sign_tolerance=self.sign_tolerance,
                )
                for event_name in events:
                    events_mid_to_right.append((comp.name, event_name))

            # 4) Check convergence: exactly one event with indicator near zero
            if len(events_left_to_mid) == 1:
                comp_name, event_name = events_left_to_mid[0]
                if abs(indicators_mid[comp_name][event_name]) <= self.tol_value:
                    return mid, events_left_to_mid
                # Continue bisecting to get closer to this single event
                right = mid
                indicators_at_right = indicators_mid
                last_events = events_left_to_mid
            elif len(events_left_to_mid) > 1:
                # Multiple events in [left, mid], narrow to find the earliest
                right = mid
                indicators_at_right = indicators_mid
                last_events = events_left_to_mid
            else:
                # No events in [left, mid], the event must be in [mid, right]
                left = mid
                indicators_at_left = indicators_mid
                last_events = events_mid_to_right

        # Return the best estimate: use the interval boundary with events
        return_time = mid if last_events else right
        
        # If we have events, return them
        if last_events:
            return return_time, last_events

        # Fallback: return the event with smallest indicator value at mid
        events_at_mid: List[Tuple[str, str]] = []
        for comp in event_sources:
            if comp.name in indicators_mid:
                for event_name, value in indicators_mid[comp.name].items():
                    if abs(value) <= self.tol_value * 10:
                        events_at_mid.append((comp.name, event_name))

        return return_time, events_at_mid if events_at_mid else last_events

    def _evaluate_indicators_at(
        self,
        event_sources: List["CoSimComponent"],
        snapshots: Dict[str, Any],
        input_cache: Dict[str, Dict[str, Any]],
        t_left: float,
        t_target: float,
    ) -> Dict[str, Dict[str, float]]:
        indicators: Dict[str, Dict[str, float]] = {}
        for comp in event_sources:
            indicators[comp.name] = self._evaluate_component_indicators(
                comp, snapshots[comp.name], input_cache[comp.name], t_left, t_target
            )
        return indicators

    def _evaluate_component_indicators(
        self,
        comp: "CoSimComponent",
        snapshot: Any,
        inputs: Dict[str, Any],
        t_left: float,
        t_target: float,
    ) -> Dict[str, float]:
        self._restore_with_inputs(comp, snapshot, inputs, t_left)
        comp.do_step(t_left, t_target - t_left)
        return comp.evaluate_event_indicators()

    def _capture_inputs(self, comp: "CoSimComponent") -> Dict[str, Any]:
        inputs: Dict[str, Any] = {}
        for name, port in comp.inputs.items():
            value = port.get()
            if value is not None:
                inputs[name] = value
        return inputs

    def _restore_with_inputs(
        self,
        comp: "CoSimComponent",
        snapshot: Any,
        inputs: Dict[str, Any],
        t: float,
    ) -> None:
        try:
            comp.restore_state(snapshot, t=t)
        except TypeError:
            comp.restore_state(snapshot)
        if inputs:
            comp.set_inputs(inputs, t=t)
