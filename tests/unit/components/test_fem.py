"""Unit tests for syssimx.components.fem.FEMComponent."""

from pathlib import Path

import pytest

from syssimx.components.fem import FEMComponent


class DummyFEM(FEMComponent):
    """Minimal concrete FEM component for testing base behavior."""

    def __init__(self, name: str, label: str | None = None, group: str | None = None):
        super().__init__(name=name, label=label, group=group)
        self.init_called = False
        self.step_called = False
        self.update_called = False
        self.last_t0: float | None = None

    def _initialize_component(self, t0: float) -> None:
        self.init_called = True
        self.last_t0 = t0

    def _do_step_internal(self, t: float, dt: float) -> None:
        self.step_called = True

    def _update_output_states(self, t=None, event_names=None) -> None:
        self.update_called = True

    def get_state(self):
        return {}

    def set_state(self, state, t: float) -> None:
        self.last_t0 = t


def test_fem_component_is_abstract():
    """FEMComponent cannot be instantiated directly."""
    with pytest.raises(TypeError):
        FEMComponent("fem")


def test_fem_component_defaults():
    """Default FEMComponent fields are initialized."""
    comp = DummyFEM("FEM", label="FEM Label", group="Group")

    assert comp.name == "FEM"
    assert comp.label == "FEM Label"
    assert comp.group == "Group"
    assert comp.geometry is None
    assert comp.mesh is None
    assert comp.spaces == {}
    assert comp.gfs == {}
    assert comp.gfs_history == {}
    assert comp.bfa is None
    assert comp.lf is None
    assert comp.solver is None
    assert comp.scene is None


def test_fem_component_initialize_calls_hook():
    """initialize calls FEM-specific hook and updates time."""
    comp = DummyFEM("FEM")
    comp.initialize(t0=1.25)

    assert comp.init_called is True
    assert comp.update_called is True
    assert comp.t == 1.25
    assert comp._is_initialized is True


def test_fem_component_do_step_calls_hooks():
    """do_step invokes the step and output update hooks."""
    comp = DummyFEM("FEM")
    comp.initialize(t0=0.0)
    comp.do_step(t=0.0, dt=0.1)

    assert comp.step_called is True
    assert comp.update_called is True
    assert comp.t == 0.1


def test_fem_optional_methods_raise():
    """Optional FEM hooks raise by default."""
    comp = DummyFEM("FEM")

    with pytest.raises(NotImplementedError):
        comp.load_mesh_from_file(Path("mesh.vtk"))

    with pytest.raises(NotImplementedError):
        comp.export_results(Path("results.vtk"))

    with pytest.raises(NotImplementedError):
        comp.visualize_state()
