"""
Root conftest.py - shared fixtures for all tests.
"""

from pathlib import Path

import pytest

# Import shared test components
from tests.fixtures.components import (
    GainComponent,
    HybridSource,
    IntegratorComponent,
    MockSubComponent,
    SimpleMultiComponent,
)


@pytest.fixture
def test_data_dir() -> Path:
    """Return path to test data directory."""
    return Path(__file__).parent / "fixtures"


# ============================================================================
# Basic Component Fixtures
# ============================================================================
@pytest.fixture
def gain_component() -> GainComponent:
    """Create a fresh GainComponent instance."""
    return GainComponent(name="TestGain", gain=2.0)


@pytest.fixture
def gain_component_initialized() -> GainComponent:
    """Create and initialize a GainComponent."""
    comp = GainComponent(name="TestGain", gain=2.0)
    comp.initialize(t0=0.0)
    return comp


@pytest.fixture
def integrator_component() -> IntegratorComponent:
    """Create a fresh IntegratorComponent instance."""
    return IntegratorComponent(name="TestIntegrator", x0=0.0)


@pytest.fixture
def integrator_component_initialized() -> IntegratorComponent:
    """Create and initialize an IntegratorComponent."""
    comp = IntegratorComponent(name="TestIntegrator", x0=0.0)
    comp.initialize(t0=0.0)
    return comp


# ============================================================================
# Hybrid Component Fixtures
# ============================================================================
@pytest.fixture
def hybrid_source() -> HybridSource:
    """Create a fresh HybridSource instance."""
    return HybridSource(name="TestHybridSource", x0=0.0)


@pytest.fixture
def hybrid_source_initialized() -> HybridSource:
    """Create and initialize a HybridSource."""
    comp = HybridSource(name="TestHybridSource", x0=0.0)
    comp.initialize(t0=0.0)
    return comp


# ============================================================================
# MultiComponent Fixtures
# ============================================================================
@pytest.fixture
def mock_sub_component() -> MockSubComponent:
    """Create a fresh MockSubComponent instance."""
    return MockSubComponent(name="TestMock", gain=1.0)


@pytest.fixture
def simple_multi_component() -> SimpleMultiComponent:
    """Create a fresh SimpleMultiComponent instance."""
    return SimpleMultiComponent(name="TestMulti", initial_mode="A")


@pytest.fixture
def simple_multi_component_initialized() -> SimpleMultiComponent:
    """Create and initialize a SimpleMultiComponent."""
    comp = SimpleMultiComponent(name="TestMulti", initial_mode="A")
    comp.initialize(t0=0.0)
    return comp
