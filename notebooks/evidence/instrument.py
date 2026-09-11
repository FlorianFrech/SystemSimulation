"""Attribute every model call to the algorithm phase that issued it.

Two levels of timer. `instrument_step` wraps each *model's*
`_do_step_internal`, which is the only measurement that means the same thing in
both cases: in the switched case the algorithm talks to the `MultiComponent`
while in the baseline it talks to the FEM directly. `instrument_algorithm`
establishes which phase is executing, so accepted work is separated from work
that is computed and then rolled back.

| Phase | Entry point | Kept? |
|---|---|---|
| `accepted` | `GaussSeidelAlgorithm.step` | yes, this is the solution |
| `trial` | `HybridAlgorithm._detect_crossings` | no, snapshotted and restored |
| `bisection` | `HybridAlgorithm._locate_event_time` | no, restored after localization |
| `events` | `HybridAlgorithm.handle_events` | yes, discrete update at the event |
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field, fields
from functools import wraps
from time import perf_counter_ns

from syssimx.system.algorithms import GaussSeidelAlgorithm, HybridAlgorithm

__all__ = [
    "ACCEPTED",
    "TRIAL",
    "BISECTION",
    "EVENTS",
    "OTHER",
    "PHASES",
    "DISCARDED_PHASES",
    "PhaseTracker",
    "PhaseTimer",
    "instrumented_hybrid",
    "instrument_algorithm",
    "instrument_step",
]

ACCEPTED, TRIAL, BISECTION, EVENTS, OTHER = "accepted", "trial", "bisection", "events", "other"
PHASES = (ACCEPTED, TRIAL, BISECTION, EVENTS, OTHER)
DISCARDED_PHASES = (TRIAL, BISECTION)


class PhaseTracker:
    """Which algorithm phase is executing right now.

    A stack rather than a scalar, so a nested entry point reports the innermost
    phase and restores its caller's on the way out.
    """

    def __init__(self):
        self._stack: list[str] = []

    @property
    def phase(self) -> str:
        return self._stack[-1] if self._stack else OTHER

    @contextmanager
    def scope(self, phase: str):
        self._stack.append(phase)
        try:
            yield
        finally:
            self._stack.pop()

    def wrap(self, phase: str, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with self.scope(phase):
                return func(*args, **kwargs)

        return wrapper


def instrumented_hybrid(source: HybridAlgorithm, tracker: PhaseTracker) -> HybridAlgorithm:
    """Rebuild `source` as a subclass whose phase entry points are timed.

    `HybridAlgorithm` is a `@dataclass(slots=True)` whose base declares
    `__slots__ = ()`, so its instances carry no `__dict__` and its methods
    cannot be replaced per instance: assigning one raises
    ``AttributeError: ... is read-only``. A subclass is an ordinary class, so it
    can override them, and both algorithm checks in `System` are `isinstance`
    tests that a subclass satisfies.
    """
    base = type(source)

    class InstrumentedHybrid(base):
        def _detect_crossings(self, *args, **kwargs):
            with tracker.scope(TRIAL):
                return super()._detect_crossings(*args, **kwargs)

        def _locate_event_time(self, *args, **kwargs):
            with tracker.scope(BISECTION):
                return super()._locate_event_time(*args, **kwargs)

        def handle_events(self, *args, **kwargs):
            with tracker.scope(EVENTS):
                return super().handle_events(*args, **kwargs)

    # The recorded `algorithm` field names the algorithm that ran, not the
    # instrumentation wrapped around it.
    InstrumentedHybrid.__name__ = base.__name__
    InstrumentedHybrid.__qualname__ = base.__qualname__

    # `name` and `missed_events` are init=False; the rest carry the tuning that
    # `assemble_system()` applied, so they have to be copied across.
    values = {f.name: getattr(source, f.name) for f in fields(source) if f.init}
    return InstrumentedHybrid(**values)


def instrument_algorithm(algorithm, tracker: PhaseTracker):
    """Label every model call with the phase that issued it.

    Returns the algorithm to run, a *new object* in the hybrid case. The caller
    has to rebind `system.algorithm` to it.
    """
    if isinstance(algorithm, HybridAlgorithm):
        algorithm = instrumented_hybrid(algorithm, tracker)
        accepted_stepper = algorithm.gauss_seidel_algorithm
    elif isinstance(algorithm, GaussSeidelAlgorithm):
        accepted_stepper = algorithm
    else:
        raise TypeError(f"Unsupported algorithm: {type(algorithm).__name__}")
    # GaussSeidelAlgorithm is a plain dataclass and keeps its __dict__, so the
    # accepted stepper is still wrapped in place.
    accepted_stepper.step = tracker.wrap(ACCEPTED, accepted_stepper.step)
    return algorithm


@dataclass
class PhaseTimer:
    """Wall time inside one component's `_do_step_internal`, split by phase."""

    label: str
    wall_ns: dict = field(default_factory=lambda: dict.fromkeys(PHASES, 0))
    n_calls: dict = field(default_factory=lambda: dict.fromkeys(PHASES, 0))

    @property
    def wall_s(self) -> float:
        return sum(self.wall_ns.values()) * 1e-9

    @property
    def calls(self) -> int:
        return sum(self.n_calls.values())

    def phase_s(self, phase: str) -> float:
        return self.wall_ns[phase] * 1e-9


def instrument_step(comp, label: str, tracker: PhaseTracker) -> PhaseTimer:
    """Wrap `comp._do_step_internal` with a phase-attributed timer.

    Counts every solver call, accepted and discarded alike, so the baseline and
    the switched case are comparable.
    """
    timer = PhaseTimer(label=label)
    original = comp._do_step_internal

    @wraps(original)
    def timed(t, dt, *args, **kwargs):
        phase = tracker.phase
        start = perf_counter_ns()
        try:
            return original(t, dt, *args, **kwargs)
        finally:
            timer.wall_ns[phase] += perf_counter_ns() - start
            timer.n_calls[phase] += 1

    comp._do_step_internal = timed
    return timer
