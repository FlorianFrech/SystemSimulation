from typing import Protocol, Dict, Any, runtime_checkable

@runtime_checkable
class CoSimComponent(Protocol):
    """
    Minimal interface for a co-simulation component (FMU, OpenSim model, etc.).
    Implementations do not need to inherit from this class,
    but must implement the methods defined here (structural subtyping).
    """
    name: str

    def initialize(self, t0: float) -> None:
        """Prepare the component for simulation starting at time t0."""
        ...

    def set_inputs(self, **signals: float) -> None:
        """Set the input signals for the next step."""
        ...

    def step(self, t: float, h: float) -> None:
        """Advance the component's state from time t to t+h."""
        ...

    def get_outputs(self) -> Dict[str, float]:
        """Return the current outputs as a dictionary {name: value}."""
        ...
    
    def reset(self) -> None:
        """Reset the component to a clean state before (before initialization)."""
        ...