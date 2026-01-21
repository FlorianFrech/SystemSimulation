"""
Unit tests for syssimx.core.multi_comp

Tests the MultiComponent base class and Hysteresis helper class.
Uses mock sub-components to isolate unit behavior.
"""

from typing import Any

import numpy as np
import pytest

from syssimx.core.multi_comp import Hysteresis, ModeKey
from syssimx.utilities import Quantity
from tests.fixtures.components import (
    EmptyMultiComponent,
    MockSubComponent,
    SimpleMultiComponent,
)


# ============================================================================
# Test Hysteresis Class
# ============================================================================
class TestHysteresis:
    """Test Hysteresis class for mode switching debouncing."""

    def test_construction(self):
        """Test Hysteresis object construction and initial state."""
        h = Hysteresis(dwell_time=0.1)
        assert np.isclose(h.dwell_time, 0.1)
        assert np.isclose(h.last_switch_time, 0.0)
        assert h.last_mode == ""

    def test_record_switch(self):
        """Test recording a mode switch."""
        h = Hysteresis(dwell_time=0.2)
        h.record_switch(t=0.0, new_mode="A")
        assert h.last_mode == "A"
        assert np.isclose(h.last_switch_time, 0.0)

    def test_can_switch(self):
        """Test disabling mode switching."""
        h = Hysteresis(dwell_time=0.2)
        h.last_mode = "A"
        assert not h.can_switch(t=0.1, proposed_mode="B")
        assert h.can_switch(t=0.3, proposed_mode="B")


# ============================================================================
# Test MultiComponent Initialization
# ============================================================================
class TestMultiComponentInitialization:
    """Test MultiComponent initialization logic."""

    def test_construction(self):
        mc = SimpleMultiComponent(name="TestMulti", initial_mode="A")
        assert mc.name == "TestMulti"
        assert mc.active_mode == "A"
        assert mc.active_comp == mc.models["A"]
        assert mc.models == {
            "A": mc.models["A"],
            "B": mc.models["B"],
        }

    def test_initialize_register_models(self):
        mc = SimpleMultiComponent(name="TestMulti", initial_mode="A")
        mc.initialize(t0=0.0)
        assert "A" in mc.models
        assert "B" in mc.models
        assert mc.active_mode == "A"
        assert isinstance(mc.active_comp, MockSubComponent)

    def test_initialize_port_unification(self):
        mc = SimpleMultiComponent(name="TestMulti", initial_mode="A")
        mc.initialize(t0=0.0)
        # Check that ports are unified correctly
        for port_name in mc.input_specs:
            assert port_name in mc.active_comp.input_specs
        for port_name in mc.output_specs:
            assert port_name in mc.active_comp.output_specs

    def test_initialize_invalid_mode(self):
        with pytest.raises(ValueError):
            mc = SimpleMultiComponent(name="TestMulti", initial_mode="C")
            mc.initialize(t0=0.0)

    def test_initialize_empty_models(self):
        mc = EmptyMultiComponent(name="EmptyMulti")
        with pytest.raises(RuntimeError):
            mc.initialize(t0=0.0)


# ============================================================================
# Test Mode Switching
# ============================================================================
class TestModeSwitching:
    """Test mode switching mechanics."""

    @pytest.fixture
    def multi_comp(self) -> SimpleMultiComponent:
        mc = SimpleMultiComponent(name="TestMulti", initial_mode="A")
        mc.initialize(t0=0.0)
        return mc

    def test_switch_mode_success(self, multi_comp: SimpleMultiComponent):
        """Test successful mode switch."""
        multi_comp._switch_mode(new_mode="B", t=0.2)
        assert multi_comp.active_mode == "B"
        assert isinstance(multi_comp.active_comp, MockSubComponent)

    def test_switch_mode_invalid(self, multi_comp: SimpleMultiComponent):
        """Test switching to an invalid mode."""
        with pytest.raises(ValueError):
            multi_comp._switch_mode(new_mode="C", t=0.2)

    def test_switch_mode_transfers_state(self, multi_comp: SimpleMultiComponent):
        """Test that state is transferred correctly on mode switch."""
        # Set some state in mode A
        state_a = {"x": 1.0, "v": 0.5}
        multi_comp.active_comp.set_state(state=state_a, t=0.1)

        # Switch to mode B
        multi_comp._switch_mode(new_mode="B", t=0.2)

        # Check that mode B received the correct state
        state_b = multi_comp.active_comp.get_state()
        assert state_b == state_a

    def test_switch_mode_records_sync_event(self, multi_comp: SimpleMultiComponent):
        """Test that mode switch records synchronization event."""
        state_a = {"x": 2.0, "v": 1.0}
        multi_comp.active_comp.set_state(state=state_a, t=0.1)
        multi_comp._switch_mode(new_mode="B", t=0.2)

        sync_events = multi_comp.sync_events
        assert len(sync_events) == 1
        event = sync_events[0]
        assert np.isclose(event["time"], 0.2)
        assert event["from_mode"] == "A"
        assert event["to_mode"] == "B"
        assert event["retrieved"] == state_a
        assert event["now"] == state_a


# ============================================================================
# Test Time Stepping
# ============================================================================
class TestTimestepping:
    """Test do_step delegation and mode switching during steps."""

    @pytest.fixture
    def multi_comp(self) -> SimpleMultiComponent:
        mc = SimpleMultiComponent(name="TestMulti", initial_mode="A")
        mc.initialize(t0=0.0)
        return mc

    def test_do_step_delegates_to_active_component(self, multi_comp: SimpleMultiComponent):
        multi_comp.do_step(t=0.0, dt=0.01)
        assert "do_step(0.0, 0.01)" in multi_comp.active_comp.call_log

    def test_do_step_with_mode_selector(self, multi_comp):
        def selector(t: float, state: dict[str, Any]) -> ModeKey:
            return "B" if t >= 0.5 else "A"

        multi_comp.mode_selector = selector
        multi_comp.do_step(t=0.0, dt=0.1)
        assert multi_comp.active_mode == "A"
        multi_comp.do_step(t=0.5, dt=0.1)
        assert multi_comp.active_mode == "B"

    def test_do_step_mode_switching_disabled(self, multi_comp: SimpleMultiComponent):
        def selector(t: float, state: dict[str, Any]) -> ModeKey:
            return "B"

        multi_comp.mode_selector = selector
        multi_comp._allow_mode_switching = False
        multi_comp.do_step(t=0.0, dt=0.1)
        assert multi_comp.active_mode == "A"

    def test_do_step_hysteresis_blocks_rapid_switch_back(self, multi_comp: SimpleMultiComponent):
        def selector(t: float, state: dict[str, Any]) -> ModeKey:
            return "B" if t < 0.1 else "A"

        multi_comp.mode_selector = selector
        multi_comp.hysteresis = Hysteresis(dwell_time=0.05)

        multi_comp.do_step(t=0.0, dt=0.01)
        assert multi_comp.active_mode == "A"  # Switch to B not allowed yet

        multi_comp.do_step(t=0.05, dt=0.01)
        assert multi_comp.active_mode == "B"  # Switch to B allowed


# ============================================================================
# Test Input/Output Delegation
# ============================================================================
class TestInputOutputDelegation:
    """Test input and output delegation to sub-components."""

    @pytest.fixture
    def multi_comp(self) -> SimpleMultiComponent:
        mc = SimpleMultiComponent(name="TestMulti", initial_mode="A")
        mc.initialize(t0=0.0)
        return mc

    def test_set_inputs_delegates_to_all_models(self, multi_comp: SimpleMultiComponent):
        multi_comp.set_inputs({"u": 10.0}, t=0.0)

        # Both models should have received the input
        for mode, comp in multi_comp.models.items():
            input = comp.inputs["u"].get()
            input_value = input.magnitude if isinstance(input, Quantity) else input
            assert np.isclose(input_value, 10.0)

    def test_update_outputs_copies_from_active(self, multi_comp: SimpleMultiComponent):
        # Set state and step to produce output
        multi_comp.active_comp.set_state({"x": 7.5, "v": 0.0}, t=0.0)
        multi_comp.active_comp._update_output_states(t=0.0)

        # Update MultiComponent outputs
        multi_comp._update_output_states(t=0.0)

        assert multi_comp.outputs["y"].get() == Quantity(7.5, "m")


# ============================================================================
# Test State Management Delegation
# ============================================================================
class TestStateDelegation:
    """Test get_state and set_state delegation."""

    @pytest.fixture
    def multi_comp(self) -> SimpleMultiComponent:
        mc = SimpleMultiComponent(name="TestMulti", initial_mode="A")
        mc.initialize(t0=0.0)
        return mc

    def test_get_state_returns_active_state(self, multi_comp: SimpleMultiComponent):
        multi_comp.active_comp.set_state({"x": 3.0, "v": 1.5}, t=0.0)

        state = multi_comp.get_state()

        assert np.isclose(state["x"], 3.0)
        assert np.isclose(state["v"], 1.5)

    def test_set_state_sets_active_state(self, multi_comp: SimpleMultiComponent):
        multi_comp.set_state({"x": 4.0, "v": 2.0}, t=0.5)

        state = multi_comp.active_comp.get_state()
        assert np.isclose(state["x"], 4.0)
        assert np.isclose(state["v"], 2.0)


# ============================================================================
# Test Reset
# ============================================================================
class TestReset:
    """Test reset functionality."""

    def test_reset_resets_all_subcomponents(self):
        mc = SimpleMultiComponent(name="TestMulti", initial_mode="A")
        mc.initialize(t0=0.0)

        # Modify states
        for comp in mc.models.values():
            comp.set_state({"x": 99.0, "v": 99.0}, t=1.0)

        mc.reset()

        # All components should be reset
        for comp in mc.models.values():
            assert "reset()" in comp.call_log
