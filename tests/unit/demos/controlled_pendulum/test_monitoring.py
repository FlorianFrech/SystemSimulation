"""Unit tests for the shared PendulumMonitor.

The monitoring panel has no FEM/ngsolve dependency, so these tests run in any
environment.
"""

from __future__ import annotations

import pytest

from syssimx.core.port import PortSpec, PortType
from syssimx_examples.controlled_pendulum.monitoring import (
    PendulumMonitor,
    PendulumMonitoringState,
)


def _specs():
    inputs = {
        "tau": PortSpec("tau", PortType.REAL, "in", unit="N.m"),
        "omega_invert": PortSpec("omega_invert", PortType.EVENT, "in"),
    }
    outputs = {
        "theta": PortSpec("theta", PortType.REAL, "out", unit="rad"),
        "omega": PortSpec("omega", PortType.REAL, "out", unit="rad/s"),
        "alpha": PortSpec("alpha", PortType.REAL, "out", unit="rad/s^2"),
    }
    return inputs, outputs


class _FakePort:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
def test_state_defaults():
    s = PendulumMonitoringState()
    assert s.time == 0.0
    assert s.mode == "FEM"
    assert s.gap == 0.0


# ---------------------------------------------------------------------------
# Widget construction
# ---------------------------------------------------------------------------
def test_monitor_builds_only_real_port_widgets():
    inputs, outputs = _specs()
    mon = PendulumMonitor(inputs, outputs, t_end=2.0, tau=1e-3, mode="FEM", with_contact=False)
    # REAL ports + time/dt/mode; the EVENT port omega_invert is excluded; no gap.
    assert set(mon.widgets) == {"tau", "theta", "omega", "alpha", "time", "dt", "mode"}


def test_contact_adds_gap_widget_and_link():
    inputs, outputs = _specs()
    mon = PendulumMonitor(inputs, outputs, t_end=2.0, tau=1e-3, with_contact=True)
    assert "gap" in mon.widgets
    # time, dt, mode, tau, theta, omega, alpha, gap
    assert len(mon._links) == 8


def test_initial_mode_sets_state_and_widget():
    inputs, outputs = _specs()
    mon = PendulumMonitor(inputs, outputs, t_end=1.0, tau=1e-3, mode="OpenSim")
    assert mon.state.mode == "OpenSim"
    assert mon.widgets["mode"].value == "OpenSim"


# ---------------------------------------------------------------------------
# Decoupling: state -> widgets via dlink
# ---------------------------------------------------------------------------
def test_state_updates_propagate_to_widgets():
    inputs, outputs = _specs()
    mon = PendulumMonitor(inputs, outputs, t_end=2.0, tau=1e-3, with_contact=True)
    mon.state.theta = 1.25
    mon.state.gap = 0.07
    mon.state.mode = "FMU"
    assert mon.widgets["theta"].value == pytest.approx(1.25)
    assert mon.widgets["gap"].value == pytest.approx(0.07)
    assert mon.widgets["mode"].value == "FMU"


# ---------------------------------------------------------------------------
# sync_from_ports
# ---------------------------------------------------------------------------
def test_sync_from_ports_mirrors_values():
    inputs, outputs = _specs()
    mon = PendulumMonitor(inputs, outputs, t_end=1.0, tau=1e-3)
    mon.sync_from_ports(
        {"tau": _FakePort(3.5)},
        {"theta": _FakePort(0.5), "omega": _FakePort(-2.0), "alpha": _FakePort(0.0)},
    )
    assert mon.state.tau == pytest.approx(3.5)
    assert mon.state.theta == pytest.approx(0.5)
    assert mon.state.omega == pytest.approx(-2.0)


def test_sync_from_ports_handles_pint_quantity():
    from syssimx.utilities.units import ureg

    inputs, outputs = _specs()
    mon = PendulumMonitor(inputs, outputs, t_end=1.0, tau=1e-3)
    mon.sync_from_ports(
        {"tau": _FakePort(2.0 * ureg("N*m"))},
        {"theta": _FakePort(0.25 * ureg("rad"))},
    )
    assert mon.state.tau == pytest.approx(2.0)
    assert mon.state.theta == pytest.approx(0.25)


def test_sync_from_ports_ignores_none():
    inputs, outputs = _specs()
    mon = PendulumMonitor(inputs, outputs, t_end=1.0, tau=1e-3)
    mon.state.theta = 9.0
    mon.sync_from_ports({}, {"theta": _FakePort(None)})
    assert mon.state.theta == pytest.approx(9.0)  # unchanged


# ---------------------------------------------------------------------------
# Teardown
# ---------------------------------------------------------------------------
def test_close_releases_links_and_stops_propagation():
    inputs, outputs = _specs()
    mon = PendulumMonitor(inputs, outputs, t_end=1.0, tau=1e-3, with_contact=True)
    mon.close()
    assert mon._links == []
    # After close, state changes no longer reach the widgets.
    mon.state.theta = 5.0
    assert mon.widgets["theta"].value == pytest.approx(0.0)
