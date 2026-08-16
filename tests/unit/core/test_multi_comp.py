"""
Unit tests for syssimx.core.multi_comp

Tests the MultiComponent base class and Hysteresis helper class.
Uses mock sub-components to isolate unit behavior.
"""

import numpy as np
import pytest

from syssimx.core.multi_comp import Hysteresis, ModeKey
from syssimx.utilities import Quantity
from tests.fixtures.components import (
    EmptyMultiComponent,
    MockSubComponent,
    SimpleMultiComponent,
    SwitchableMultiComponent,
    UnitMismatchMultiComponent,
)


def _magnitude(value, default: float = 0.0) -> float:
    """Unwrap a port value, which may be a Pint ``Quantity``."""
    if value is None:
        return default
    return float(getattr(value, "magnitude", value))


# ============================================================================
# Test Hysteresis Class
# ============================================================================
class TestHysteresis:
    """Test Hysteresis class for mode switching debouncing."""

    def test_construction(self):
        """Test Hysteresis object construction and initial state."""
        h = Hysteresis(dwell_time=0.1)
        assert np.isclose(h.dwell_time, 0.1)
        assert h.last_switch_time == -float("inf")

    def test_record_switch(self):
        """Test recording a mode switch."""
        h = Hysteresis(dwell_time=0.2)
        h.record_switch(t=0.3)
        assert np.isclose(h.last_switch_time, 0.3)

    def test_in_dwell_window(self):
        """Dwell window starts open after a switch and closes once the dwell time has elapsed."""
        h = Hysteresis(dwell_time=0.2)
        assert not h.in_dwell_window(t=0.0)  # No prior switch: window already closed
        h.record_switch(t=0.0)
        assert h.in_dwell_window(t=0.1)      # 0.1 s < 0.2 s dwell
        assert not h.in_dwell_window(t=0.3)  # 0.3 s >= 0.2 s dwell


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

    def test_initialize_initializes_all_models(self):
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

    def test_construct_empty_models_rejected(self):
        """An empty models map is rejected at construction time."""
        with pytest.raises(ValueError):
            EmptyMultiComponent(name="EmptyMulti")

    def test_initialize_incompatible_ports_unit_mismatch(self):
        with pytest.raises(ValueError):
            UnitMismatchMultiComponent(name="UnitMismatch")


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

    def test_switch_mode_records_minimal_sync_event_by_default(
        self, multi_comp: SimpleMultiComponent
    ):
        """Each switch logs time, from_mode, to_mode; state fields are omitted by default."""
        multi_comp._switch_mode(new_mode="B", t=0.2)

        sync_events = multi_comp.sync_events
        assert len(sync_events) == 1
        event = sync_events[0]
        assert np.isclose(event["time"], 0.2)
        assert event["from_mode"] == "A"
        assert event["to_mode"] == "B"
        assert "retrieved" not in event
        assert "now" not in event

    def test_switch_mode_records_state_when_enabled(self, multi_comp: SimpleMultiComponent):
        """Enabling record_switch_state adds the pre- and post-switch state snapshots."""
        state_a = {"x": 2.0, "v": 1.0}
        multi_comp.active_comp.set_state(state=state_a, t=0.1)
        multi_comp.record_switch_state = True

        multi_comp._switch_mode(new_mode="B", t=0.2)

        event = multi_comp.sync_events[0]
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
        def selector(t: float) -> ModeKey:
            return "B" if t >= 0.5 else "A"

        multi_comp.mode_selector = selector
        multi_comp.do_step(t=0.0, dt=0.1)
        assert multi_comp.active_mode == "A"
        multi_comp.do_step(t=0.5, dt=0.1)
        assert multi_comp.active_mode == "B"

    def test_do_step_mode_switching_disabled(self, multi_comp: SimpleMultiComponent):
        def selector(t: float) -> ModeKey:
            return "B"

        multi_comp.mode_selector = selector
        multi_comp._allow_mode_switching = False
        multi_comp.do_step(t=0.0, dt=0.1)
        assert multi_comp.active_mode == "A"

    def test_do_step_hysteresis_blocks_rapid_switch_back(self, multi_comp: SimpleMultiComponent):
        """Hysteresis prevents a second switch within the dwell window after the first switch."""
        targets = iter(["B", "A", "A"])

        def selector(t: float) -> ModeKey:
            return next(targets)

        multi_comp.mode_selector = selector
        multi_comp.hysteresis = Hysteresis(dwell_time=0.05)

        multi_comp.do_step(t=0.0, dt=0.01)
        assert multi_comp.active_mode == "B"  # First switch: dwell window was empty

        multi_comp.do_step(t=0.02, dt=0.01)
        assert multi_comp.active_mode == "B"  # Blocked: still inside dwell window

        multi_comp.do_step(t=0.10, dt=0.01)
        assert multi_comp.active_mode == "A"  # Allowed: dwell window closed

    def test_record_history_propagates_to_active_component(
        self, multi_comp: SimpleMultiComponent
    ):
        """A trial step disables ``_record_history`` on the MultiComponent.

        The flag must propagate to the active sub-component so that the
        inner ``do_step`` (which would otherwise record) does not pollute
        the active model's history during hybrid event localization. This
        is the regression guard for the previously dead ``_record_history``
        suppression in the hybrid algorithm.
        """
        active = multi_comp.active_comp
        before = len(active.history.get_port_history("y"))

        # Simulate the hybrid trial-step contract: disable recording on the
        # MultiComponent and advance via the internal step entry point.
        multi_comp._record_history = False
        multi_comp._do_step_internal(t=0.0, dt=0.01)

        assert active._record_history is False
        assert len(active.history.get_port_history("y")) == before  # not recorded

    def test_record_history_enabled_records_on_active_component(
        self, multi_comp: SimpleMultiComponent
    ):
        """Normal stepping (recording enabled) still records the active
        sub-component's history."""
        active = multi_comp.active_comp
        before = len(active.history.get_port_history("y"))

        multi_comp.do_step(t=0.0, dt=0.01)

        assert active._record_history is True
        assert len(active.history.get_port_history("y")) == before + 1


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

    def test_set_inputs_forwards_only_to_active(self, multi_comp: SimpleMultiComponent):
        """Only the active sub-component receives inputs on each call."""
        multi_comp.set_inputs({"u": 10.0}, t=0.0)

        active_value = multi_comp.active_comp.inputs["u"].get()
        active_value = (
            active_value.magnitude if isinstance(active_value, Quantity) else active_value
        )
        assert np.isclose(active_value, 10.0)

        inactive = multi_comp.models["B"]
        inactive_value = inactive.inputs["u"].get()
        inactive_value = (
            inactive_value.magnitude if isinstance(inactive_value, Quantity) else inactive_value
        )
        # Inactive model has not received the new input (still at its initial value).
        assert inactive_value is None or not np.isclose(inactive_value, 10.0)

    def test_switch_replays_cached_inputs_to_target(self, multi_comp: SimpleMultiComponent):
        """On a mode switch, the cached inputs are replayed onto the target model."""
        multi_comp.set_inputs({"u": 10.0}, t=0.0)
        multi_comp._switch_mode(new_mode="B", t=0.1)

        # The newly active component is model "B" and must now hold the cached input.
        replayed = multi_comp.active_comp.inputs["u"].get()
        replayed = replayed.magnitude if isinstance(replayed, Quantity) else replayed
        assert np.isclose(replayed, 10.0)

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


# ============================================================================
# Test Switch Indicators (event-localized mode switching)
# ============================================================================
class TestSwitchIndicatorRegistration:
    """Test registration and validation of switch indicators."""

    def test_registers_indicator_and_event_port(self):
        mc = SwitchableMultiComponent(name="Plant")
        mc.add_switch_indicator(
            name="to_fast",
            func=lambda c: c.outputs["y"].get() - 1.0,
            target_mode="FAST",
            direction=1,
        )
        mc.initialize(t0=0.0)

        assert "to_fast" in mc.event_indicators
        assert mc._switch_targets["to_fast"] == "FAST"
        # The wrapper exposes the switch as an ordinary EVENT output port.
        assert "to_fast" in mc.output_specs
        assert mc.has_state_events

    def test_rejects_unknown_target_mode(self):
        mc = SwitchableMultiComponent(name="Plant")
        with pytest.raises(ValueError, match="Unknown target mode"):
            mc.add_switch_indicator("bad", lambda c: 0.0, target_mode="NOPE")

    def test_rejects_name_colliding_with_submodel_indicator(self):
        mc = SwitchableMultiComponent(name="Plant")
        mc.models["SLOW"].add_event_indicator("shared", lambda c: 1.0)
        with pytest.raises(KeyError, match="collides"):
            mc.add_switch_indicator("shared", lambda c: 0.0, target_mode="FAST")

    def test_rejects_registration_after_initialization(self):
        mc = SwitchableMultiComponent(name="Plant")
        mc.initialize(t0=0.0)

        with pytest.raises(RuntimeError, match="before initialization"):
            mc.add_switch_indicator("to_fast", lambda c: 0.0, target_mode="FAST")

    def test_unify_ports_preserves_switch_event_port(self):
        """``_unify_ports`` copies sub-model specs; own event ports must survive."""
        mc = SwitchableMultiComponent(name="Plant")
        mc.add_switch_indicator("to_fast", lambda c: 0.0, target_mode="FAST")
        mc.initialize(t0=0.0)

        mc._unify_ports()

        assert "to_fast" in mc.output_specs


class TestSwitchIndicatorEvaluation:
    """Test that switch indicators join the normal event pipeline."""

    def test_indicators_merge_wrapper_and_active_model(self):
        mc = SwitchableMultiComponent(name="Plant")
        mc.models["SLOW"].add_event_indicator("physics", lambda c: 5.0)
        mc.add_switch_indicator("to_fast", lambda c: -2.0, target_mode="FAST")
        mc.initialize(t0=0.0)

        values = mc.evaluate_event_indicators()

        assert np.isclose(values["physics"], 5.0)
        assert np.isclose(values["to_fast"], -2.0)

    def test_indicator_receives_the_wrapper(self):
        """The switch function is evaluated against the wrapper, not the sub-model."""
        seen: list = []
        mc = SwitchableMultiComponent(name="Plant")
        mc.add_switch_indicator("to_fast", lambda c: seen.append(c) or 1.0, target_mode="FAST")
        mc.initialize(t0=0.0)

        mc.evaluate_event_indicators()

        assert seen and seen[0] is mc

    def test_detect_crossings_covers_both_sources(self):
        mc = SwitchableMultiComponent(name="Plant")
        mc.models["SLOW"].add_event_indicator("physics", lambda c: 1.0)
        mc.add_switch_indicator("to_fast", lambda c: 1.0, target_mode="FAST")
        mc.initialize(t0=0.0)

        crossed = mc.detect_event_crossings(
            previous={"physics": -1.0, "to_fast": -1.0},
            current={"physics": 1.0, "to_fast": 1.0},
        )

        assert set(crossed) == {"physics", "to_fast"}


class TestSwitchOnEvent:
    """Test that the switch is applied when the localized event is handled."""

    def _plant(self, initial_mode: ModeKey = "SLOW"):
        mc = SwitchableMultiComponent(name="Plant", initial_mode=initial_mode)
        mc.add_switch_indicator(
            name="to_fast",
            func=lambda c: c.outputs["y"].get() - 1.0,
            target_mode="FAST",
            direction=1,
        )
        mc.initialize(t0=0.0)
        return mc

    def test_handling_switch_event_changes_mode(self):
        mc = self._plant()
        assert mc.active_mode == "SLOW"

        mc.handle_event(["to_fast"], t=1.0)

        assert mc.active_mode == "FAST"
        assert mc.active_comp is mc.models["FAST"]

    def test_switch_transfers_state_to_incoming_model(self):
        mc = self._plant()
        mc.do_step(0.0, 1.0)  # SLOW ramps y to 1.0

        mc.handle_event(["to_fast"], t=1.0)

        assert np.isclose(mc.models["FAST"].get_state()["y"], 1.0)

    def test_switch_refreshes_the_incoming_model_outputs(self):
        """Regression: the incoming model must publish the transferred state.

        A model that has been inactive still holds the outputs it wrote when it
        was last active. If the switch does not refresh them, the wrapper copies
        those stale values and the recorded trajectory shows a jump at the
        handover even though the physical state is continuous.
        """
        mc = self._plant()
        # Leave a stale value on the incoming model, as an earlier activation would.
        mc.models["FAST"].outputs["y"].set(-99.0, t=0.0)
        mc.do_step(0.0, 1.0)  # SLOW ramps y to 1.0

        mc.handle_event(["to_fast"], t=1.0)

        assert np.isclose(_magnitude(mc.models["FAST"].outputs["y"].get()), 1.0)
        assert np.isclose(_magnitude(mc.outputs["y"].get()), 1.0)

    def test_no_switch_when_target_already_active(self):
        mc = self._plant(initial_mode="FAST")
        mc.handle_event(["to_fast"], t=1.0)
        assert mc.active_mode == "FAST"
        assert mc.sync_events == []

    def test_model_events_still_reach_the_active_component(self):
        handled: list = []
        mc = self._plant()
        mc.models["SLOW"]._handle_events_internal = lambda names, t: handled.append((names, t))

        mc.handle_event(["physics", "to_fast"], t=1.0)

        # The physics event goes to the outgoing model, and only that event.
        assert handled == [(["physics"], 1.0)]
        assert mc.active_mode == "FAST"

    def test_dwell_window_suppresses_switch(self):
        mc = self._plant()
        mc.hysteresis = Hysteresis(dwell_time=0.5)
        mc.hysteresis.record_switch(t=1.0)

        mc.handle_event(["to_fast"], t=1.2)  # 0.2 s < 0.5 s dwell

        assert mc.active_mode == "SLOW"

    def test_disabled_switching_suppresses_switch(self):
        """The hybrid algorithm disables switching during rolled-back trial steps."""
        mc = self._plant()
        mc._allow_mode_switching = False

        mc.handle_event(["to_fast"], t=1.0)

        assert mc.active_mode == "SLOW"

    def test_unrelated_event_does_not_switch(self):
        mc = self._plant()
        mc.handle_event(["something_else"], t=1.0)
        assert mc.active_mode == "SLOW"


class TestLegacySwitchingUnaffected:
    """Guard the pre-existing ``mode_selector`` path against regressions.

    ``add_event_indicator`` broadcasts to the sub-models and keeps a copy on
    the wrapper for port management only. The switch-indicator work must not
    start treating those copies as wrapper-owned indicators.
    """

    def test_broadcast_indicator_is_evaluated_on_the_active_model_only(self):
        seen: list[str] = []

        def indicator(comp):
            seen.append(comp.name)
            return 1.0

        mc = SwitchableMultiComponent(name="Plant")
        mc.add_event_indicator("threshold", indicator, direction=1)
        mc.initialize(t0=0.0)

        mc.evaluate_event_indicators()

        # The wrapper's own copy must not be evaluated: the sub-model is the
        # authoritative source, and evaluating both would overwrite its value.
        assert seen == ["Plant_SLOW"]

    def test_broadcast_indicator_is_not_a_switch_target(self):
        mc = SwitchableMultiComponent(name="Plant")
        mc.add_event_indicator("threshold", lambda c: 1.0, direction=1)
        mc.initialize(t0=0.0)

        assert mc._switch_targets == {}
        assert mc.self_handled_events == []
        # Handling it must reach the model, and must not switch mode.
        mc.handle_event(["threshold"], t=1.0)
        assert mc.active_mode == "SLOW"

    def test_mode_selector_still_switches_on_the_macro_grid(self):
        mc = SwitchableMultiComponent(name="Plant")
        mc.mode_selector = lambda t: "FAST" if t >= 0.5 else "SLOW"
        mc.initialize(t0=0.0)

        mc.do_step(0.0, 0.4)
        assert mc.active_mode == "SLOW"
        mc.do_step(0.4, 0.4)  # selector polled at t = 0.4 -> still SLOW
        assert mc.active_mode == "SLOW"
        mc.do_step(0.8, 0.4)  # selector polled at t = 0.8 -> FAST
        assert mc.active_mode == "FAST"
