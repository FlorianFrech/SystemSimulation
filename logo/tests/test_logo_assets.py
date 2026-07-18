from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from tools.build_logo_assets import (
    COLORS,
    LOGO_SPEC,
    MICRO_24,
    STANDARD,
    build_assets,
    favicon_16_svg,
    horizontal_svg,
    icon_svg,
    social_preview_svg,
)

NS = {"svg": "http://www.w3.org/2000/svg"}


def parse(svg: str):
    return ET.fromstring(svg)


def test_standard_icon_structure() -> None:
    root = parse(icon_svg())
    assert root.attrib["viewBox"] == "0 0 256 256"
    assert len(root.findall(".//svg:rect", NS)) == 4
    assert len(root.findall(".//svg:circle", NS)) == 4
    assert len(root.findall(".//svg:path", NS)) == 4


def test_brand_colors_are_present() -> None:
    svg = icon_svg(palette="light")
    assert COLORS.navy in svg
    assert COLORS.cyan in svg
    assert COLORS.white in svg


def test_builder_uses_machine_readable_spec() -> None:
    assert COLORS.navy == LOGO_SPEC["colors"]["navy"]
    assert STANDARD.node_size == LOGO_SPEC["standard"]["node_size"]


def test_geometry_is_symmetric() -> None:
    assert STANDARD.node_position + STANDARD.node_size == 72
    assert STANDARD.far_node_position == 184
    assert 72 + 184 == 256


def test_24px_master_is_optically_strengthened() -> None:
    assert MICRO_24.connector_stroke > STANDARD.connector_stroke
    assert MICRO_24.node_stroke > STANDARD.node_stroke
    assert MICRO_24.port_radius > STANDARD.port_radius


def test_native_favicon_grid() -> None:
    root = parse(favicon_16_svg())
    assert root.attrib["viewBox"] == "0 0 16 16"


def test_dark_lockup_background_matches_viewbox() -> None:
    root = parse(horizontal_svg("dark"))
    viewbox_width = root.attrib["viewBox"].split()[2]
    background = root.find("svg:rect", NS)
    assert background is not None
    assert background.attrib["width"] == viewbox_width


def test_horizontal_wordmark_has_no_gap_before_x() -> None:
    root = parse(horizontal_svg("light"))
    text = root.find("svg:text", NS)
    assert text is not None
    first, last = text.findall("svg:tspan", NS)
    assert first.text == "SysSim"
    assert first.tail in (None, "")
    assert last.text == "X"


def test_social_preview_geometry() -> None:
    root = parse(social_preview_svg())
    assert root.attrib["viewBox"] == "0 0 1280 640"
    background = root.find("svg:rect", NS)
    assert background is not None
    assert background.attrib["fill"] == COLORS.navy


def test_build_creates_expected_files(tmp_path: Path) -> None:
    output = build_assets(tmp_path / "logo", create_zip=False)
    expected = [
        output / "svg" / "syssimx_icon_primary.svg",
        output / "svg" / "syssimx_icon_micro_24.svg",
        output / "svg" / "syssimx_horizontal_light.svg",
        output / "png" / "syssimx_icon_16px.png",
        output / "png" / "syssimx_icon_24px.png",
        output / "png" / "syssimx_icon_32px.png",
        output / "png" / "syssimx_app_icon_solid_navy_1024px.png",
        output / "png" / "syssimx_social_preview_1280x640.png",
        output / "svg" / "syssimx_social_preview.svg",
        output / "syssimx_favicon.ico",
        output / "build_info.json",
    ]
    for path in expected:
        assert path.exists(), path

    ico = (output / "syssimx_favicon.ico").read_bytes()
    assert int.from_bytes(ico[4:6], "little") == 3
