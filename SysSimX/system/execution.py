# framework/system/engine.py
from __future__ import annotations
from typing import Dict, Any, List
from .system import System
from .connection import Connection

class ExecutionEngine:
    """
    Two-phase per-generation:
      1) set inputs for all components in the generation
      2) do_step on all components in the generation (can be parallelized)
    """

    def initialize(self, sys: System, t0: float) -> None:
        for c in sys.components.values():
            c.initialize(t0)

    def _collect_outputs(self, sys: System) -> Dict[str, Dict[str, Any]]:
        return {name: comp.get_outputs() for name, comp in sys.components.items()}

    def _set_inputs_for_generation(self, sys: System, gen: List[str], outputs: Dict[str, Dict[str, Any]]) -> None:
        for comp_name in gen:
            inputs: Dict[str, Any] = {}
            for con in sys.connections:
                if con.dst_comp.name != comp_name: continue
                # choose source value: current outputs for delay=0, previous outputs for delay>0
                src_vals = outputs.get(con.src_comp, {})
                val = src_vals.get(con.src_port, None)
                if val is not None:
                    inputs[con.dst_port] = val
            sys.components[comp_name].set_inputs(**inputs)

    def step(self, sys: System, t: float, dt: float) -> None:
        execution_order = sys.execution_order
        outputs = self._collect_outputs(sys)
        for gen in execution_order:
            self._set_inputs_for_generation(sys, gen, outputs)
            # compute all in gen (sequential for now; swap to ThreadPoolExecutor later)
            for comp_name in gen:
                sys.components[comp_name].do_step(t, dt)

    def run(self, sys: System, t0: float, t_end: float, dt: float) -> None:
        self.initialize(sys, t0)
        t = t0
        while t < t_end - 1e-15:
            self.step(sys, t, dt)
            t += dt
        # (optional) finalize/shutdown later
