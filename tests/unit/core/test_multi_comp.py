"""
Unit tests for syssimx.core.multi_comp

Tests the MultiComponent base class and region-switching domain model.
Uses mock sub-components to isolate unit behavior.
"""

from dataclasses import FrozenInstanceError

import numpy as np
import pytest

from syssimx.core.events import Event
from syssimx.core.multi_comp import SwitchRegions
from syssimx.utilities import Quantity
from tests.fixtures.components import (
    EmptyMultiComponent,
    MockSubComponent,
    NoRollbackComponent,
    RegionMultiComponent,
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

    def test_record_history_propagates_to_active_component(self, multi_comp: SimpleMultiComponent):
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
# Test Generated Region Events
# ============================================================================
class TestGeneratedRegionEventRegistration:
    """Test registration and validation of generated region boundaries."""

    @staticmethod
    def configure(mc: RegionMultiComponent) -> None:
        mc.set_switch_regions(
            key=lambda comp: _magnitude(comp.outputs["y"].get()),
            breakpoints=(1.0,),
            modes=("A", "B"),
            band=0.1,
        )

    def test_registers_indicator_and_event_port(self):
        mc = RegionMultiComponent(name="Plant")
        self.configure(mc)
        mc.initialize(t0=0.0)

        assert "region_boundary_0" in mc.event_indicators
        assert "region_boundary_0" in mc.output_specs
        assert mc.has_state_events

    def test_rejects_unknown_target_mode(self):
        mc = RegionMultiComponent(name="Plant")
        with pytest.raises(ValueError, match="Unknown region models.*NOPE"):
            mc.set_switch_regions(
                key=lambda comp: 0.0,
                breakpoints=(1.0,),
                modes=("A", "NOPE"),
                band=0.1,
            )

    def test_rejects_name_colliding_with_submodel_indicator(self):
        mc = RegionMultiComponent(name="Plant")
        mc.models["A"].add_event_indicator("region_boundary_0", lambda c: 1.0)
        with pytest.raises(KeyError, match="collides"):
            self.configure(mc)

    def test_rejects_registration_after_initialization(self):
        mc = RegionMultiComponent(name="Plant")
        mc.initialize(t0=0.0)

        with pytest.raises(RuntimeError, match="before initialization"):
            self.configure(mc)

    def test_unify_ports_preserves_generated_event_port(self):
        """``_unify_ports`` copies sub-model specs; own event ports must survive."""
        mc = RegionMultiComponent(name="Plant")
        self.configure(mc)
        mc.initialize(t0=0.0)

        mc._unify_ports()

        assert "region_boundary_0" in mc.output_specs


class TestGeneratedRegionEventEvaluation:
    """Test that generated boundaries join the normal event pipeline."""

    @staticmethod
    def configure(mc: RegionMultiComponent, key=None) -> None:
        mc.set_switch_regions(
            key=key or (lambda comp: _magnitude(comp.outputs["y"].get())),
            breakpoints=(1.0,),
            modes=("A", "B"),
            band=0.1,
        )

    def test_indicators_merge_wrapper_and_active_model(self):
        mc = RegionMultiComponent(name="Plant")
        mc.models["A"].add_event_indicator("physics", lambda c: 5.0)
        self.configure(mc)
        mc.initialize(t0=0.0)

        values = mc.evaluate_event_indicators()

        assert np.isclose(values["physics"], 5.0)
        assert np.isclose(values["region_boundary_0"], -1.1)

    def test_region_key_receives_the_wrapper(self):
        seen: list = []
        mc = RegionMultiComponent(name="Plant")
        self.configure(mc, key=lambda comp: seen.append(comp) or 0.0)
        mc.initialize(t0=0.0)

        mc.evaluate_event_indicators()

        assert seen and seen[0] is mc

    def test_detect_crossings_covers_both_sources(self):
        mc = RegionMultiComponent(name="Plant")
        mc.models["A"].add_event_indicator("physics", lambda c: 1.0)
        self.configure(mc)
        mc.initialize(t0=0.0)

        crossed = mc.detect_event_crossings(
            previous={"physics": -1.0, "region_boundary_0": -1.0},
            current={"physics": 1.0, "region_boundary_0": 1.0},
        )

        assert set(crossed) == {"physics", "region_boundary_0"}


class TestRegionSwitchOnEvent:
    """Test that a generated boundary switches at its localized event."""

    @staticmethod
    def _plant():
        mc = RegionMultiComponent(name="Plant", signal=lambda t: t)
        mc.set_switch_regions(
            key=lambda comp: _magnitude(comp.outputs["y"].get()),
            breakpoints=(1.0,),
            modes=("A", "B"),
            band=0.1,
        )
        mc.initialize(t0=0.0)
        return mc

    @staticmethod
    def _rising_event(mc: RegionMultiComponent) -> Event:
        return Event(name="region_boundary_0", source=mc.name, direction=1)

    def test_handling_switch_event_changes_mode(self):
        mc = self._plant()
        assert mc.active_mode == "A"

        mc.handle_event(["region_boundary_0"], t=1.1, events=[self._rising_event(mc)])

        assert mc.active_mode == "B"
        assert mc.active_comp is mc.models["B"]
        assert mc.active_region_index == 1

    def test_switch_transfers_state_to_incoming_model(self):
        mc = self._plant()
        mc.do_step(0.0, 1.1)

        mc.handle_event(["region_boundary_0"], t=1.1, events=[self._rising_event(mc)])

        assert np.isclose(mc.models["B"].get_state()["y"], 1.1)

    def test_switch_refreshes_the_incoming_model_outputs(self):
        """Regression: the incoming model must publish the transferred state.

        A model that has been inactive still holds the outputs it wrote when it
        was last active. If the switch does not refresh them, the wrapper copies
        those stale values and the recorded trajectory shows a jump at the
        handover even though the physical state is continuous.
        """
        mc = self._plant()
        mc.models["B"].outputs["y"].set(-99.0, t=0.0)
        mc.do_step(0.0, 1.1)

        mc.handle_event(["region_boundary_0"], t=1.1, events=[self._rising_event(mc)])

        assert np.isclose(_magnitude(mc.models["B"].outputs["y"].get()), 1.1)
        assert np.isclose(_magnitude(mc.outputs["y"].get()), 1.1)

    def test_model_events_still_reach_the_active_component(self):
        handled: list = []
        mc = self._plant()
        mc.models["A"]._handle_events_internal = lambda names, t: handled.append((names, t))

        events = [
            Event(name="physics", source=mc.name, direction=1),
            self._rising_event(mc),
        ]
        mc.handle_event(["physics", "region_boundary_0"], t=1.1, events=events)

        assert handled == [(["physics"], 1.1)]
        assert mc.active_mode == "B"

    def test_disabled_switching_suppresses_switch(self):
        mc = self._plant()
        mc._allow_mode_switching = False

        mc.handle_event(["region_boundary_0"], t=1.1, events=[self._rising_event(mc)])

        assert mc.active_mode == "A"
        assert mc.active_region_index == 0

    def test_unrelated_event_does_not_switch(self):
        mc = self._plant()
        mc.handle_event(["something_else"], t=1.0)
        assert mc.active_mode == "A"


class TestOrdinaryModelEvents:
    """Ordinary model events remain delegated independently of switching."""

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

        assert mc.self_handled_events == []
        mc.handle_event(["threshold"], t=1.0)
        assert mc.active_mode == "SLOW"


class TestSwitchRegions:
    """Validate the immutable region domain and authoritative runtime identity."""

    @staticmethod
    def regions() -> SwitchRegions:
        return SwitchRegions(
            key=lambda comp: _magnitude(comp.outputs["y"].get()),
            breakpoints=(5.0, 15.0, 25.0),
            modes=("A", "B", "A", "C"),
            band=(0.5, 1.0, 1.5),
        )

    def test_n_models_require_exactly_n_minus_one_boundaries(self):
        regions = self.regions()

        assert len(regions.modes) == 4
        assert len(regions.boundaries) == 3
        with pytest.raises(ValueError, match="exactly 3 boundaries"):
            SwitchRegions(lambda comp: 0.0, (5.0, 15.0), regions.modes, band=0.5)

    def test_configuration_and_boundaries_are_immutable(self):
        regions = self.regions()

        with pytest.raises(FrozenInstanceError):
            regions.modes = ("A", "B")
        with pytest.raises(FrozenInstanceError):
            regions.boundaries[0].band = 2.0

        plant = RegionMultiComponent()
        with pytest.raises(AttributeError):
            plant.switch_regions = regions

    def test_each_boundary_is_represented_by_one_bidirectional_indicator(self):
        plant = RegionMultiComponent()
        plant.set_switch_regions(
            key=lambda comp: _magnitude(comp.outputs["y"].get()),
            breakpoints=(5.0, 15.0, 25.0),
            modes=("A", "B", "A", "C"),
            band=0.5,
        )

        assert len(plant.switch_regions.boundaries) == 3
        assert list(plant.event_indicators) == [
            "region_boundary_0",
            "region_boundary_1",
            "region_boundary_2",
        ]
        assert {indicator.direction for indicator in plant.event_indicators.values()} == {0}

    def test_every_reachable_region_model_must_support_rollback(self):
        plant = RegionMultiComponent()
        plant.models["B"] = NoRollbackComponent("no_rollback")

        with pytest.raises(RuntimeError, match="Every region model must support rollback.*B"):
            plant.set_switch_regions(
                key=lambda comp: _magnitude(comp.outputs["y"].get()),
                breakpoints=(5.0,),
                modes=("A", "B"),
                band=0.5,
            )

    def test_initialization_reconciles_the_region_once(self):
        plant = RegionMultiComponent(signal=lambda t: 20.0, initial_mode="A")
        plant.set_switch_regions(
            key=lambda comp: _magnitude(comp.outputs["y"].get()),
            breakpoints=(5.0, 15.0),
            modes=("A", "B", "C"),
            band=0.5,
        )

        plant.initialize(0.0)

        assert plant.active_region_index == 2
        assert plant.active_mode == "C"
        assert plant.sync_events == []

    def test_region_map_is_not_polled_during_accepted_steps(self):
        evaluations = 0

        def key(comp):
            nonlocal evaluations
            evaluations += 1
            return _magnitude(comp.outputs["y"].get())

        plant = RegionMultiComponent(signal=lambda t: t)
        plant.set_switch_regions(key, breakpoints=(5.0,), modes=("A", "B"), band=0.5)
        plant.initialize(0.0)
        assert evaluations == 1

        plant.do_step(0.0, 0.1)

        assert evaluations == 1

    def test_inconsistent_runtime_region_raises(self):
        plant = RegionMultiComponent()
        plant.set_switch_regions(
            key=lambda comp: _magnitude(comp.outputs["y"].get()),
            breakpoints=(5.0, 15.0),
            modes=("A", "B", "C"),
            band=0.5,
        )
        plant.initialize(0.0)
        plant.active_region_index = 99

        with pytest.raises(RuntimeError, match="Invalid active_region_index"):
            _ = plant.active_mode


class TestTransactionalRegionSwitching:
    """A rejected target preparation must be invisible to the accepted run."""

    @staticmethod
    def _observable_state(comp):
        return {
            "time": comp.t,
            "inputs": {name: (port.get(), port.t_last) for name, port in comp.inputs.items()},
            "outputs": {name: (port.get(), port.t_last) for name, port in comp.outputs.items()},
            "history": {
                name: (tuple(data["time"]), tuple(data["values"]))
                for name, data in comp.get_history().items()
            },
        }

    def test_failed_target_import_restores_entire_transaction(self, monkeypatch):
        plant = RegionMultiComponent(signal=lambda t: t)
        plant.set_switch_regions(
            key=lambda comp: _magnitude(comp.outputs["y"].get()),
            breakpoints=(5.0,),
            modes=("A", "B"),
            band=0.5,
        )
        plant.initialize(0.0)
        plant.do_step(0.0, 1.0)

        source = plant.models["A"]
        target = plant.models["B"]
        wrapper_before = self._observable_state(plant)
        source_before = self._observable_state(source)
        source_physical_before = source.get_state()
        target_before = self._observable_state(target)
        target_physical_before = target.get_state()

        def reject_import(state, t):
            target._time = 99.0
            target._y = 99.0
            target.t = 99.0
            target.outputs["y"].set(99.0, t=99.0)
            target._record_outputs(99.0)
            raise ValueError("target rejected state")

        monkeypatch.setattr(target, "set_state", reject_import)

        with pytest.raises(ValueError, match="target rejected state"):
            plant._switch_region(1, t=1.0)

        assert plant.active_region_index == 0
        assert plant.active_mode == "A"
        assert plant.active_comp is source
        assert plant.sync_events == []
        assert self._observable_state(plant) == wrapper_before
        assert self._observable_state(source) == source_before
        assert source.get_state() == source_physical_before
        assert self._observable_state(target) == target_before
        assert target.get_state() == target_physical_before

    def test_failed_domain_validation_restores_entire_transaction(self, monkeypatch):
        plant = RegionMultiComponent(signal=lambda t: t)
        plant.set_switch_regions(
            key=lambda comp: _magnitude(comp.outputs["y"].get()),
            breakpoints=(5.0,),
            modes=("A", "B"),
            band=0.5,
        )
        plant.initialize(0.0)
        plant.do_step(0.0, 1.0)

        source = plant.models["A"]
        target = plant.models["B"]
        wrapper_before = self._observable_state(plant)
        source_before = self._observable_state(source)
        source_physical_before = source.get_state()
        target_before = self._observable_state(target)
        target_physical_before = target.get_state()

        def reject_transfer(*_args):
            raise RuntimeError("physical continuity rejected")

        monkeypatch.setattr(plant, "_build_transfer_report", reject_transfer)

        with pytest.raises(RuntimeError, match="physical continuity rejected"):
            plant._switch_region(1, t=1.0)

        assert plant.active_region_index == 0
        assert plant.active_mode == "A"
        assert plant.active_comp is source
        assert plant.sync_events == []
        assert self._observable_state(plant) == wrapper_before
        assert self._observable_state(source) == source_before
        assert source.get_state() == source_physical_before
        assert self._observable_state(target) == target_before
        assert target.get_state() == target_physical_before

    def test_reset_reinitialize_matches_fresh_equivalent_instance(self):
        def build():
            plant = RegionMultiComponent(signal=lambda t: 20.0, initial_mode="A")
            plant.set_switch_regions(
                key=lambda comp: _magnitude(comp.outputs["y"].get()),
                breakpoints=(5.0, 15.0),
                modes=("A", "B", "C"),
                band=0.5,
            )
            return plant

        reused = build()
        reused.initialize(0.0)
        reused.do_step(0.0, 1.0)
        reused.sync_events.append({"time": 1.0, "from_mode": "C", "to_mode": "B"})
        reused.reset()
        reused.initialize(3.0)

        fresh = build()
        fresh.initialize(3.0)

        assert reused.active_region_index == fresh.active_region_index == 2
        assert reused.active_mode == fresh.active_mode == "C"
        assert reused.sync_events == fresh.sync_events == []
        assert self._observable_state(reused) == self._observable_state(fresh)
        for mode in reused.models:
            assert self._observable_state(reused.models[mode]) == self._observable_state(
                fresh.models[mode]
            )
