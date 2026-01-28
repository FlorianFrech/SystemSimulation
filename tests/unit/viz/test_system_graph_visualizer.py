"""Unit tests for SystemGraphVisualizer."""

from __future__ import annotations

import pytest

import syssimx.viz.system_graph_visualizer as viz_mod
from syssimx.viz.system_graph_visualizer import SystemGraphVisualizer
from tests.fixtures.systems import (
    create_simple_hybrid_system,
    create_small_algebraic_loop_system,
    create_visualizer_continuous_system,
)


@pytest.fixture
def no_graphviz_render(monkeypatch):
    """Disable graph rendering/display for visualization tests."""

    def fake_render(self, filename: str, view: bool = False, cleanup: bool = False):
        return filename

    monkeypatch.setattr(viz_mod.Digraph, "render", fake_render, raising=False)
    monkeypatch.setattr(viz_mod, "display", lambda *args, **kwargs: None)


class TestSystemGraphVisualizer:
    def test_visualizer_continuous_system_features(self, no_graphviz_render):
        system, comps = create_visualizer_continuous_system()
        system.build_graphs()
        system.compute_execution_order()

        viz = SystemGraphVisualizer(system)
        viz.visualize(filename="continuous_system", format="svg")

        assert viz.dot is not None
        src = viz.dot.source

        # Group clusters and legend
        assert "cluster_Reference" in src
        assert "cluster_Control" in src
        assert "cluster_legend" in src

        # Ungrouped component should appear (Plant is ungrouped)
        assert "Plant" in src

        # Unit label on edge to unitful input
        assert "[N*m]" in src

        # Direct feedthrough output highlighting
        assert 'COLOR="#ef4444"' in src

        # Multi-input ports appear as anchors
        assert 'PORT="pos"' in src
        assert 'PORT="neg"' in src

        # Execution index badge is rendered
        assert 'POINT-SIZE="8">#' in src

    def test_visualizer_algebraic_loop_edges_highlighted(self, no_graphviz_render):
        system, comp_a, comp_b = create_small_algebraic_loop_system()
        system.build_graphs()
        system.compute_execution_order()

        assert system.algebraic_loops

        viz = SystemGraphVisualizer(system)
        viz.visualize(filename="algebraic_loop", format="svg")
        src = viz.dot.source

        # Algebraic loop edges are colored red and thickened
        assert 'color="#ef4444"' in src
        assert "penwidth=2.0" in src or 'penwidth="2.0"' in src

    def test_visualizer_hybrid_event_edges_and_ports(self, no_graphviz_render):
        system, source, listener, combi, gain = create_simple_hybrid_system()
        system.build_graphs()
        system.compute_execution_order()

        viz = SystemGraphVisualizer(system)
        viz.visualize(filename="hybrid_system", format="svg")
        src = viz.dot.source

        # Event edges are dashed with odot arrowheads and blue color
        assert "style=dashed" in src or 'style="dashed"' in src
        assert "arrowhead=odot" in src or 'arrowhead="odot"' in src
        assert 'color="#0b84ff"' in src

        # Event ports are highlighted in blue
        assert "trigger" in src
        assert 'COLOR="#0b84ff"' in src
        assert "v_invert" in src

    def test_visualizer_save_requires_visualize(self):
        system, _ = create_visualizer_continuous_system()
        viz = SystemGraphVisualizer(system)

        with pytest.raises(RuntimeError, match="visualized"):
            viz.save("should_fail.svg")
