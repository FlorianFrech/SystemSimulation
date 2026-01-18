"""
Unit tests for syssimx.core.events
Tests event handling using hybrid test components.
"""

import numpy as np
import pytest

from syssimx.core.events import DenseTime, EventIndicator, InternalEventInfo, _sign
from tests.fixtures.components import HybridSource


# ============================================================================
# Test _sign Functionality
# ============================================================================
class TestSignFunction:
    """Test _sign function behavior."""

    def test_positive(self):
        value = 9.9e-10
        tol = 1.0e-10
        assert _sign(value, tol=tol) == 1

    def test_negative(self):
        value = -9.9e-10
        tol = 1.0e-10
        assert _sign(value, tol=tol) == -1

    def test_zero(self):
        value = 5.0e-11
        tol = 1.0e-10
        assert _sign(value, tol=tol) == 0


# ============================================================================
# Test DenseTime Functionality
# ============================================================================
class TestDenseTime:
    """Test DenseTime class functionality."""

    def test_construction_and_comparison(self):
        dt1 = DenseTime(1.0, 0)
        dt2 = DenseTime(1.0, 1)
        dt3 = DenseTime(2.0, 0)

        assert dt1 < dt2
        assert dt2 < dt3
        assert dt1 < dt3
        assert dt1 == DenseTime(1.0, 0)

    def test_advance_micro(self):
        dt = DenseTime(1.0, 0)
        dt_advanced = dt.advance_micro()
        assert np.isclose(dt_advanced.t, 1.0)
        assert dt_advanced.micro == 1

    def test_to_float(self):
        dt = DenseTime(1.5, 3)
        assert np.isclose(dt.to_float(), 1.5)


# ============================================================================
# Test Event Indicator Functionality
# ============================================================================
class TestEventIndicator:
    """Test EventIndicator class functionality."""

    def test_construction_valid(self):
        def func(comp: HybridSource) -> float:
            return comp.x

        indicator = EventIndicator(name="test_indicator", function=func, direction=0)
        assert indicator.name == "test_indicator"
        assert indicator.direction == 0
        assert indicator.function is func

    def test_invalid_direction(self):
        def func(comp: HybridSource) -> float:
            return comp.x

        with pytest.raises(ValueError):
            EventIndicator(name="invalid_indicator", function=func, direction=2)

    def test_evaluation(self):
        comp = HybridSource(name="HybridSource", x0=5.0)
        comp.initialize(t0=0.0)

        def func(comp: HybridSource) -> float:
            return comp.x - 10.0

        ei = EventIndicator(name="position_indicator", function=func, direction=0)
        value = ei.evaluate(component=comp)
        assert np.isclose(value, -5.0)

    def test_invalid_evaluation(self):
        comp = HybridSource(name="HybridSource")
        comp.initialize(t0=0.0)

        def func(comp: float) -> float:
            return comp

        ei = EventIndicator(name="invalid_function", function=func, direction=0)
        with pytest.raises(TypeError):
            ei.evaluate(component=comp)


# ============================================================================
# Test Internal Event Info Functionality
# ============================================================================
class TestInternalEventInfo:
    """Test InternalEventInfo class functionality."""

    def test_valid_construction(self):
        t_before = 1.234567
        t_after = 2.345678
        interval_width = t_after - t_before
        info = InternalEventInfo(event_name="test_event", t_before=t_before, t_after=t_after)
        assert info.event_name == "test_event"
        assert info.t_before == t_before
        assert info.t_after == t_after
        assert np.isclose(info.interval_width, interval_width)
