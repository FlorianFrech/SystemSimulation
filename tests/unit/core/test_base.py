"""
Unit tests for syssimx.core.base

Tests CoSimComponent base class functionality using the Gain component.
"""

import numpy as np
import pytest

from syssimx.core.base import CoSimComponent
from syssimx.core.events import Event, EventIndicator
from syssimx.core.port import PortSpec, PortState, PortType
from syssimx.utilities.units import ureg
from tests.fixtures.components import (
    GainComponent,
    HybridCombi,
    HybridListener,
    HybridSource,
    IntegratorComponent,
)


# ============================================================================
# Test CoSimComponent Basics
# ============================================================================
class TestCoSimComponentBasics:
    """Test CoSimComponent creation and basic properties."""

    def test_construction(self):
        comp = GainComponent(name="Gain", gain=2.0)
        assert comp.name == "Gain"
        assert isinstance(comp, GainComponent)
        assert isinstance(comp, CoSimComponent)

        # Port specifications
        u_port_spec = PortSpec(
            name="u", type=PortType.REAL, direction="in", unit="N*m", description="Input torque"
        )
        y_port_spec = PortSpec(
            name="y",
            type=PortType.REAL,
            direction="out",
            unit="rad/s",
            description="Output angular velocity",
        )
        assert comp.input_specs["u"] == u_port_spec
        assert comp.output_specs["y"] == y_port_spec

    def test_parameter_getting_setting_validation(self):
        comp = GainComponent(name="Gain", gain=2.0)
        assert comp.get_parameters("k") == {"k": 2.0}

        comp.set_parameters(k=3.5)
        assert comp.get_parameters("k") == {"k": 3.5}

        with pytest.raises(TypeError):
            comp.set_parameters(k="invalid")  # k must be float or int

        with pytest.raises(KeyError):
            comp.set_parameters(nonexistent=1.0)  # nonexistent parameter

    def test_initialization(self):
        comp = GainComponent(name="Gain", gain=2.0)
        comp.initialize(t0=0.0)  # NOW ports exist
        assert "u" in comp.inputs
        assert "y" in comp.outputs
        assert isinstance(comp.inputs["u"], PortState)
        assert isinstance(comp.outputs["y"], PortState)

        # Check default values
        u_value = comp.inputs["u"].get()
        assert u_value is not None
        assert np.isclose(u_value.magnitude, 0.0)  # Default REAL value

        y_value = comp.outputs["y"].get()
        assert y_value is not None
        assert np.isclose(y_value.magnitude, 0.0)  # 2.0 * 0.0

    def test_set_inputs(self):
        comp = GainComponent(name="Gain", gain=2.0)
        comp.initialize(t0=0.0)
        inputs = {"u": 5.0 * ureg("N*m")}
        comp.set_inputs(inputs, t=0.0)
        assert np.isclose(comp.inputs["u"].get().magnitude, 5.0)
        assert np.isclose(comp.inputs["u"].t_last, 0.0)

    def test_evaluate_outputs(self):
        comp = GainComponent(name="Gain", gain=2.0)
        comp.initialize(t0=0.0)
        inputs = {"u": 4.0 * ureg("N*m")}
        outputs = comp.evaluate_outputs(inputs)
        assert np.isclose(outputs["y"].magnitude, 8.0)  # 2.0 * 4.0
        assert outputs["y"].is_compatible_with(ureg("rad/s"))

    def test_get_outputs(self):
        comp = GainComponent(name="Gain", gain=2.0)
        comp.initialize(t0=0.0)
        inputs = {"u": 3.0 * ureg("N*m")}
        comp.set_inputs(inputs, t=0.0)
        comp._update_output_states(t=1.0)
        outputs = comp.get_outputs()
        assert np.isclose(outputs["y"].magnitude, 6.0)  # 2.0 * 3.0
        assert outputs["y"].is_compatible_with(ureg("rad/s"))

    def test_do_step(self):
        comp = IntegratorComponent(x0=0.0)
        comp.initialize(t0=0.0)
        inputs = {"u": 1.0}  # constant input (rate of change)
        comp.set_inputs(inputs, t=0.0)
        comp.do_step(t=0.0, dt=1.0)
        outputs = comp.get_outputs()
        history = comp.get_history()

        assert np.isclose(comp.t, 1.0)  # Current time after step
        assert np.isclose(outputs["y"], 1.0)  # Integrated value should be
        assert np.isclose(history["y"]["values"][0], 0.0)  # History should show initial value
        assert np.isclose(history["y"]["values"][1], 1.0)  # and updated value


# ============================================================================
# Test CoSimComponent Hybrid Functionality
# ============================================================================
class TestCoSimComponentHybrid:
    """Test CoSimComponent hybrid features using a simple hybrid component."""

    class TestEventIndicator:
        """A simple hybrid component for testing event indicators."""

        def test_add_event_indicator(self):
            comp = HybridSource("HybridComp", x0=0.0, v=1.0, t0=0.0)
            comp.initialize(t0=0.0)

            def event_function(c: HybridSource) -> float:
                return c.x

            assert not comp.has_state_events
            comp.add_event_indicator(name="test_event", func=event_function, direction=1)
            assert comp.has_state_events
            assert "test_event" in comp.event_indicators

        def test_duplicate_event_indicator(self):
            comp = HybridSource("HybridComp", x0=0.0, v=1.0, t0=0.0)
            comp.initialize(t0=0.0)

            def event_function(c: HybridSource) -> float:
                return c.x

            comp.add_event_indicator(name="test_event", func=event_function, direction=1)
            with pytest.raises(KeyError):
                comp.add_event_indicator(name="test_event", func=event_function, direction=1)

        def test_invalid_event_direction(self):
            comp = HybridSource("HybridComp", x0=0.0, v=1.0, t0=0.0)
            comp.initialize(t0=0.0)

            def event_function(c: HybridSource) -> float:
                return c.x

            with pytest.raises(ValueError):
                comp.add_event_indicator(
                    name="invalid_direction_event", func=event_function, direction=2
                )  # Invalid direction

        def test_evaluate_event_indicators(self):
            comp = HybridSource("HybridComp", x0=0.0, v=1.0, t0=0.0)
            comp.initialize(t0=0.0)
            comp.add_event_indicator(name="test_event", func=lambda c: c.x, direction=1)
            # Initially x=0.0
            value = comp.evaluate_event_indicators()["test_event"]
            assert np.isclose(value, 0.0)

            # Advance time to t=1.0, x should be 1.0
            comp.do_step(t=0.0, dt=1.0)
            value = comp.evaluate_event_indicators()["test_event"]
            assert np.isclose(value, 1.0)

    class TestEventDetection:
        """Test event detection mechanism in hybrid components."""

        def test_event_detection_rising(self):
            comp = HybridSource("HybridComp", x0=-1.0, v=1.0, t0=0.0)
            comp.initialize(t0=0.0)
            comp.add_event_indicator(name="test_event", func=lambda c: c.x, direction=1)
            indicators_prev = comp.evaluate_event_indicators()
            # Advance time to t=2.0, x should be 1.0 (crossed zero)
            comp.do_step(t=0.0, dt=2.0)
            indicators_curr = comp.evaluate_event_indicators()
            crossed = comp.detect_event_crossings(previous=indicators_prev, current=indicators_curr)
            assert "test_event" in crossed

        def test_event_detection_falling(self):
            comp = HybridSource("HybridComp", x0=1.0, v=-1.0, t0=0.0)
            comp.initialize(t0=0.0)
            comp.add_event_indicator(name="test_event", func=lambda c: c.x, direction=-1)
            indicators_prev = comp.evaluate_event_indicators()
            # Advance time to t=2.0, x should be -1.0 (crossed zero)
            comp.do_step(t=0.0, dt=2.0)
            indicators_curr = comp.evaluate_event_indicators()
            crossed = comp.detect_event_crossings(previous=indicators_prev, current=indicators_curr)
            assert "test_event" in crossed

        def test_event_detection_both_directions(self):
            comp = HybridSource("HybridComp", x0=-1.0, v=2.0, t0=0.0)
            comp.initialize(t0=0.0)
            comp.add_event_indicator(name="test_event", func=lambda c: c.x, direction=0)
            indicators_prev = comp.evaluate_event_indicators()
            # Advance time to t=1.0, x should be 1.0 (crossed zero)
            comp.do_step(t=0.0, dt=1.0)
            indicators_curr = comp.evaluate_event_indicators()
            crossed = comp.detect_event_crossings(previous=indicators_prev, current=indicators_curr)
            assert "test_event" in crossed

    class TestEventSubscription:
        """Test event subscription mechanism in hybrid components."""

        def test_event_subscription(self):
            comp = HybridCombi("HybridCombi", x0=0.0, v=1.0, t0=0.0)
            comp.initialize(t0=0.0)

            def event_function(c: HybridCombi) -> float:
                return c.x

            event = Event(name="source_event", source=comp.name, direction=1)
            comp.add_event_indicator(
                name=event.name, func=event_function, direction=event.direction
            )

            ei = EventIndicator(name=event.name, function=event_function, direction=event.direction)
            comp.subscribe_event(event)

            assert "source_event" in comp.event_indicators.keys()
            assert comp.event_indicators["source_event"].function == ei.function
            assert comp.event_indicators["source_event"].direction == ei.direction
            assert event in comp.event_subscriptions

        def test_has_event_subscriptions(self):
            comp = HybridCombi("HybridCombi", x0=0.0, v=1.0, t0=0.0)
            comp.initialize(t0=0.0)
            assert not comp.has_event_subscriptions

            def event_function(c: HybridCombi) -> float:
                return c.x

            event = Event(name="source_event", source=comp.name, direction=1)
            comp.add_event_indicator(
                name=event.name, func=event_function, direction=event.direction
            )
            comp.subscribe_event(event)

            assert comp.has_event_subscriptions

    class TestStateRollback:
        """Test state snapshot and rollback functionality in hybrid components."""

        def test_support_rollback(self):
            source = HybridSource("HybridComp")
            listener = HybridListener("HybridListener")
            source.initialize(t0=0.0)
            listener.initialize(t0=0.0)
            assert source.supports_rollback
            assert not listener.supports_rollback

        def test_snapshot_and_restore_state(self):
            comp = HybridCombi("HybridCombi", x0=0.0, v=1.0, t0=0.0)
            comp.initialize(t0=0.0)
            comp.do_step(t=0.0, dt=2.0)  # Advance to t=2.0
            snapshot = comp.snapshot_state()
            t_snapshot = comp.t

            # Change state
            comp.v_curr += 2.0
            comp.do_step(t=2.0, dt=1.0)  # Advance to t=3.0

            # Restore state
            comp.restore_state(snapshot, t=t_snapshot)
            assert np.isclose(comp.t, t_snapshot)
            assert np.isclose(comp.x, 2.0)  # x should be back to value at t=2.0
            assert np.isclose(comp.v_curr, 1.0)  # v should be back to initial value

        def test_restore_state_invalid(self):
            comp = HybridCombi("HybridCombi", x0=0.0, v=1.0, t0=0.0)
            comp.initialize(t0=0.0)
            snapshot = {"invalid_key": 123}  # Invalid snapshot

            with pytest.raises(KeyError):
                comp.restore_state(snapshot, t=0.0)

        def test_rollback_with_event_indicators(self):
            comp = HybridSource("HybridComp", x0=0.0, v=1.0, t0=0.0)
            comp.initialize(t0=0.0)
            comp.add_event_indicator(name="test_event", func=lambda c: c.x, direction=1)
            comp.do_step(t=0.0, dt=2.0)  # Advance to t=2.0
            indicatores_before = comp.evaluate_event_indicators()
            snapshot = comp.snapshot_state()
            t_snapshot = comp.t

            # Change state
            comp.v += 2.0
            comp.do_step(t=2.0, dt=1.0)  # Advance to t=3.0
            indicators_after = comp.evaluate_event_indicators()
            assert not np.isclose(indicatores_before["test_event"], indicators_after["test_event"])

            # Restore state
            comp.restore_state(snapshot, t=t_snapshot)
            indicators_restored = comp.evaluate_event_indicators()
            assert np.isclose(indicatores_before["test_event"], indicators_restored["test_event"])
