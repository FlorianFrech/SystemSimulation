from __future__ import annotations
from typing import Any, Dict, Optional, Callable, Protocol
from ..core.base import CoSimComponent
from ..core.port import PortSpec, PortState
from ..utilities.units import ureg, Quantity

# -------------------------------------------------------------------
# Type Aliases
# -------------------------------------------------------------------
ModeKey = str  # e.g., "FEM", "OpenSim", "EQB"

# -------------------------------------------------------------------
# State Adapter Protocol (for incompatible component interfaces)
# -------------------------------------------------------------------
class StateAdapter(Protocol):
    """Adapter to translate state between components with different interfaces."""
    def adapt_state(self, source_state: Dict[str, Any], target_component: CoSimComponent) -> Dict[str, Any]:
        """Convert state from source format to target component's expected format."""
        ...

# -------------------------------------------------------------------
# Hysteresis for Mode Switching
# -------------------------------------------------------------------
class Hysteresis:
    """Prevents chattering by enforcing minimum dwell time between switches."""
    def __init__(self, dwell_time: float = 0.03):
        self.dwell_time = dwell_time
        self.last_switch_time = 0.0
        self.last_mode: ModeKey = ""
    
    def can_switch(self, t: float, proposed_mode: ModeKey) -> bool:
        """Check if sufficient time has passed since last switch."""
        if proposed_mode == self.last_mode:
            return False  # Already in this mode
        return (t - self.last_switch_time) >= self.dwell_time
    
    def record_switch(self, t: float, new_mode: ModeKey):
        """Record a mode switch."""
        self.last_switch_time = t
        self.last_mode = new_mode

# -------------------------------------------------------------------
# Abstract MultiComponent Base Class
# -------------------------------------------------------------------
class MultiComponent(CoSimComponent):
    """
    Abstract base for components that wrap multiple interchangeable sub-components.
    
    Subclass Responsibilities:
    1. Override `_register_models()` to populate `self.models`
    2. Override `_adapt_state()` for component-specific state translation
    3. (Optional) Set `self.mode_selector` for custom switching logic
    4. (Optional) Set `self.hysteresis` for chattering prevention
    
    Base Class Handles:
    - Port unification (ensures all models have compatible ports)
    - Mode switching with hysteresis
    - State synchronization between models
    - Input/output delegation to active component
    """
    
    def __init__(self, name: str, initial_mode: ModeKey, group: Optional[str] = None):
        super().__init__(name, label=name, group=group)
        
        # Model registry: {mode_key: component}
        self.models: Dict[ModeKey, CoSimComponent] = {}
        
        # Active component tracking
        self.active_mode: ModeKey = initial_mode
        self.active_comp: Optional[CoSimComponent] = None
        
        # Mode selection strategy (default: never switch)
        self.mode_selector: Optional[Callable[[float, Dict[str, Any]], ModeKey]] = None
        
        # Hysteresis for switching (default: no hysteresis)
        self.hysteresis: Optional[Hysteresis] = None
        
        # State adapters (optional): {mode_key: adapter}
        self.state_adapters: Dict[ModeKey, StateAdapter] = {}

    # ---- Abstract Methods (must be implemented by subclass) ----
    def _register_models(self) -> None:
        """
        Register all sub-components in self.models.
        
        Example:
            self.models = {
                "FEM": FEMPendulum(...),
                "OpenSim": OpenSimPendulum(...),
                "EQB": FMUComponent(...)
            }
        """
        raise NotImplementedError(f"{self.name}: Subclass must implement _register_models()")
    
    def _adapt_state(self, state: Dict[str, Any], target_mode: ModeKey) -> Dict[str, Any]:
        """
        Adapt state from current component to target component format.
        """
        return NotImplemented(f"{self.name}: Subclass must implement _adapt_state()")

    # ---- Lifecycle (Template Methods) ----    
    def _initialize_component(self, t0: float) -> None:
        """
        Initialize all sub-components and set up port unification.
        """
        # Step 1: Register models (subclass responsibility)
        self._register_models()
        
        if not self.models:
            raise RuntimeError(f"{self.name}: No models registered in _register_models()")
        
        # Step 2: Validate initial mode
        if self.active_mode not in self.models:
            raise ValueError(f"{self.name}: Initial mode '{self.active_mode}' not in models: {list(self.models.keys())}")
        
        # Step 3: Initialize all sub-components
        for mode_key, comp in self.models.items():
            if comp is not None:
                comp.initialize(t0)
        
        # Step 4: Set active component
        self.active_comp = self.models[self.active_mode]
        
        # Step 5: Unify ports (adopt active component's port specs)
        self._unify_ports()
    
    def _unify_ports(self) -> None:
        """
        Adopt port specifications from active component and validate compatibility.
        """
        # Adopt active component's port specs
        self.input_specs = self.active_comp.input_specs.copy()
        self.output_specs = self.active_comp.output_specs.copy()
        
        # Create port states
        self._initialize_ports_from_specs()
        
        # Validate: all models must have compatible ports
        for mode_key, comp in self.models.items():
            if comp is None:
                continue
            
            # Check inputs
            for name, spec in self.input_specs.items():
                if name not in comp.input_specs:
                    raise ValueError(
                        f"{self.name}: Model '{mode_key}' missing input port '{name}'"
                    )
                # TODO: Add unit compatibility check
            
            # Check outputs
            for name, spec in self.output_specs.items():
                if name not in comp.output_specs:
                    raise ValueError(
                        f"{self.name}: Model '{mode_key}' missing output port '{name}'"
                    )

    # ---- Mode Switching Logic ----
    def _do_step_internal(self, t: float, dt: float) -> None:
        """
        Execute time step with potential mode switching.
        """
        # Step 1: Check if mode switch is needed
        if self.mode_selector is not None:
            proposed_mode = self.mode_selector(t, self.get_state())
            
            # Apply hysteresis if configured
            if self.hysteresis is not None:
                if not self.hysteresis.can_switch(t, proposed_mode):
                    proposed_mode = self.active_mode
            
            # Perform switch if mode changed
            if proposed_mode != self.active_mode:
                self._switch_mode(proposed_mode, t)
        
        # Step 2: Execute active component's time step
        self.active_comp.do_step(t, dt)

    def _switch_mode(self, new_mode: ModeKey, t: float) -> None:
        """
        Switch from active_comp to new mode with state synchronization.
        """
        if new_mode not in self.models:
            raise ValueError(f"{self.name}: Unknown mode '{new_mode}'")
        
        print(f"[{self.name}] Switching: {self.active_mode} to {new_mode} @ t={t:.4f}s")
        
        # Step 1: Get current state
        current_state = self.active_comp.get_state()
        
        # Step 2: Adapt state for new component (subclass hook)
        adapted_state = self._adapt_state(current_state, new_mode)
        
        # Step 3: Set state in new component
        new_comp = self.models[new_mode]
        new_comp.set_state(adapted_state, t)
        
        # Step 4: Update active component
        self.active_mode = new_mode
        self.active_comp = new_comp
        
        # Step 5: Record switch in hysteresis
        if self.hysteresis is not None:
            self.hysteresis.record_switch(t, new_mode)

    # ---- I/O Delegation ----
    def set_inputs(self, signals: Dict[str, Any], t: Optional[float] = None) -> None:
        """Delegate to all models (for state synchronization) or just active."""
        for comp in self.models.values():
            if comp is not None:
                comp.set_inputs(signals, t)
    
    def _update_output_states(self, t: float) -> None:
        """Copy outputs from active component to self.outputs."""
        for name in self.output_specs.keys():
            value = self.active_comp.outputs[name].get()
            if value is not None:
                self.outputs[name].set(value, t=t)

    # ---- State Management ----
    def set_state(self, state: Dict[str, Any], t: float) -> None:
        """Delegate to active component (with optional adaptation)."""
        adapted_state = self._adapt_state(state, self.active_mode)
        self.active_comp.set_state(adapted_state, t)
    
    def get_state(self) -> Dict[str, Any]:
        """Get state from active component."""
        return self.active_comp.get_state()
    
    def reset(self) -> None:
        """Reset all sub-components."""
        for comp in self.models.values():
            if comp is not None:
                comp.reset()


    

    


