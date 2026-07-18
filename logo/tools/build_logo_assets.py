from __future__ import annotations

import argparse
import json
import math
import shutil
import struct
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import cairosvg

try:
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.ttLib import TTFont
except ImportError:  # Optional unless outlined wordmarks are requested.
    SVGPathPen = None
    TTFont = None


Palette = Literal["light", "dark", "mono_dark", "mono_light"]
HorizontalPalette = Literal["light", "dark", "mono"]
MicroMode = Literal["16", "24"] | None


@dataclass(frozen=True)
class Colors:
    navy: str = "#10243E"
    cyan: str = "#00BFE8"
    white: str = "#FFFFFF"
    mono: str = "#111827"


@dataclass(frozen=True)
class Geometry:
    node_position: int
    node_size: int
    far_node_position: int
    node_radius: int
    node_stroke: int
    connector_stroke: int
    port_radius: int
    center_half_diagonal: int


SPEC_PATH = Path(__file__).resolve().parents[1] / "spec" / "logo_spec.json"


def _load_spec() -> dict:
    """Load the machine-readable brand specification used by the builder."""
    with SPEC_PATH.open(encoding="utf-8") as spec_file:
        return json.load(spec_file)


LOGO_SPEC = _load_spec()
COLORS = Colors(
    navy=LOGO_SPEC["colors"]["navy"],
    cyan=LOGO_SPEC["colors"]["cyan"],
    white=LOGO_SPEC["colors"]["white"],
    mono=LOGO_SPEC["colors"]["monochrome"],
)


def _geometry_from_spec(section: str) -> Geometry:
    values = LOGO_SPEC[section]
    return Geometry(
        node_position=values["node_position"],
        node_size=values["node_size"],
        far_node_position=values["far_node_position"],
        node_radius=values["node_corner_radius"],
        node_stroke=values["node_stroke"],
        connector_stroke=values["connector_stroke"],
        port_radius=values["port_radius"],
        center_half_diagonal=values["center_half_diagonal"],
    )


STANDARD = _geometry_from_spec("standard")
MICRO_16 = _geometry_from_spec("micro_16")
MICRO_24 = _geometry_from_spec("micro_24")


def geometry_for(mode: MicroMode) -> Geometry:
    if mode == "16":
        return MICRO_16
    if mode == "24":
        return MICRO_24
    return STANDARD


def palette_values(name: Palette) -> tuple[str, str, str, str]:
    """Return stroke, node fill, port fill, background."""
    if name == "light":
        return COLORS.navy, COLORS.white, COLORS.cyan, COLORS.white
    if name == "dark":
        return COLORS.white, COLORS.navy, COLORS.cyan, COLORS.navy
    if name == "mono_dark":
        return COLORS.mono, COLORS.white, COLORS.mono, COLORS.white
    if name == "mono_light":
        return COLORS.white, COLORS.mono, COLORS.white, COLORS.mono
    raise ValueError(f"Unsupported palette: {name}")


def icon_svg(
    *,
    palette: Palette = "light",
    solid_background: bool = False,
    micro_mode: MicroMode = None,
) -> str:
    """Build the square SysSimX icon as portable SVG."""
    stroke, node_fill, port_fill, background = palette_values(palette)
    g = geometry_for(micro_mode)

    inner_near = g.node_position + g.node_size
    inner_far = g.far_node_position

    # Butt-ended diagonal arms terminate exactly on the four edges of a
    # mathematically centered diamond. No clipping masks are required.
    edge_offset = g.center_half_diagonal / 2
    nw = 128 - edge_offset
    ne_x, ne_y = 128 + edge_offset, 128 - edge_offset
    sw_x, sw_y = 128 - edge_offset, 128 + edge_offset
    se = 128 + edge_offset

    bg = ""
    if solid_background:
        bg = f'<rect x="0" y="0" width="256" height="256" rx="52" fill="{background}"/>'

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256"
  role="img" aria-label="SysSimX icon">
  {bg}
  <g shape-rendering="geometricPrecision" stroke-linejoin="round">
    <g fill="none" stroke="{stroke}" stroke-width="{g.connector_stroke}" stroke-linecap="butt">
      <path d="M {inner_near} {inner_near} L {nw:g} {nw:g}"/>
      <path d="M {inner_far} {inner_near} L {ne_x:g} {ne_y:g}"/>
      <path d="M {inner_near} {inner_far} L {sw_x:g} {sw_y:g}"/>
      <path d="M {inner_far} {inner_far} L {se:g} {se:g}"/>
    </g>
    <g fill="{node_fill}" stroke="{stroke}" stroke-width="{g.node_stroke}">
      <rect x="{g.node_position}" y="{g.node_position}" width="{g.node_size}" height="{g.node_size}" rx="{g.node_radius}"/>
      <rect x="{g.far_node_position}" y="{g.node_position}" width="{g.node_size}" height="{g.node_size}" rx="{g.node_radius}"/>
      <rect x="{g.node_position}" y="{g.far_node_position}" width="{g.node_size}" height="{g.node_size}" rx="{g.node_radius}"/>
      <rect x="{g.far_node_position}" y="{g.far_node_position}" width="{g.node_size}" height="{g.node_size}" rx="{g.node_radius}"/>
    </g>
    <g fill="{port_fill}">
      <circle cx="{inner_near}" cy="{inner_near}" r="{g.port_radius}"/>
      <circle cx="{inner_far}" cy="{inner_near}" r="{g.port_radius}"/>
      <circle cx="{inner_near}" cy="{inner_far}" r="{g.port_radius}"/>
      <circle cx="{inner_far}" cy="{inner_far}" r="{g.port_radius}"/>
    </g>
  </g>
</svg>'''


def favicon_16_svg() -> str:
    """Native 16 x 16, pixel-hinted favicon master."""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"
  role="img" aria-label="SysSimX favicon">
  <rect width="16" height="16" rx="3" fill="{COLORS.navy}"/>
  <g fill="none" stroke="{COLORS.white}" stroke-width="1.5" stroke-linecap="butt">
    <path d="M4.5 4.5 L7.25 7.25"/>
    <path d="M11.5 4.5 L8.75 7.25"/>
    <path d="M4.5 11.5 L7.25 8.75"/>
    <path d="M11.5 11.5 L8.75 8.75"/>
  </g>
  <g fill="{COLORS.navy}" stroke="{COLORS.white}" stroke-width="1">
    <rect x="1.5" y="1.5" width="3" height="3" rx=".7"/>
    <rect x="11.5" y="1.5" width="3" height="3" rx=".7"/>
    <rect x="1.5" y="11.5" width="3" height="3" rx=".7"/>
    <rect x="11.5" y="11.5" width="3" height="3" rx=".7"/>
  </g>
  <g fill="{COLORS.cyan}">
    <circle cx="4.5" cy="4.5" r=".75"/>
    <circle cx="11.5" cy="4.5" r=".75"/>
    <circle cx="4.5" cy="11.5" r=".75"/>
    <circle cx="11.5" cy="11.5" r=".75"/>
  </g>
</svg>'''


def _glyph_paths(
    text: str,
    font_path: Path,
    font_size: float,
    x: float,
    baseline_y: float,
) -> tuple[list[str], float]:
    if TTFont is None or SVGPathPen is None:
        raise RuntimeError("fonttools is required to outline the wordmark")

    font = TTFont(str(font_path))
    glyph_set = font.getGlyphSet()
    cmap = font.getBestCmap()
    metrics = font["hmtx"].metrics
    units_per_em = font["head"].unitsPerEm
    scale = font_size / units_per_em

    elements: list[str] = []
    cursor = x
    for character in text:
        glyph_name = cmap.get(ord(character))
        if glyph_name is None:
            raise ValueError(f"Missing glyph {character!r} in {font_path}")
        pen = SVGPathPen(glyph_set)
        glyph_set[glyph_name].draw(pen)
        path_data = pen.getCommands()
        elements.append(
            f'<path d="{path_data}" transform="translate({cursor:.3f} {baseline_y:.3f}) '
            f'scale({scale:.8f} {-scale:.8f})"/>'
        )
        advance_width, _ = metrics[glyph_name]
        cursor += advance_width * scale

    font.close()
    return elements, cursor - x


def horizontal_svg(
    palette: HorizontalPalette = "light",
    *,
    inter_semibold: Path | None = None,
    inter_bold: Path | None = None,
) -> str:
    """Build the horizontal icon-plus-wordmark lockup."""
    if palette == "light":
        stroke, node_fill, port_fill = COLORS.navy, COLORS.white, COLORS.cyan
        main_fill, x_fill = COLORS.navy, COLORS.cyan
    elif palette == "dark":
        stroke, node_fill, port_fill = COLORS.white, COLORS.navy, COLORS.cyan
        main_fill, x_fill = COLORS.white, COLORS.cyan
    elif palette == "mono":
        stroke, node_fill, port_fill = COLORS.mono, COLORS.white, COLORS.mono
        main_fill = x_fill = COLORS.mono
    else:
        raise ValueError(f"Unsupported palette: {palette}")

    wordmark_x = 252
    baseline = 157
    font_size = 94

    if inter_semibold and inter_bold:
        main_paths, main_advance = _glyph_paths("SysSim", inter_semibold, font_size, wordmark_x, baseline)
        accent_x = wordmark_x + main_advance - 1.5
        accent_paths, accent_advance = _glyph_paths("X", inter_bold, font_size, accent_x, baseline)
        viewbox_width = math.ceil(accent_x + accent_advance + 22)
        wordmark = (
            f'<g fill="{main_fill}">{"".join(main_paths)}</g>'
            f'<g fill="{x_fill}">{"".join(accent_paths)}</g>'
        )
    else:
        viewbox_width = 720
        wordmark = f'''<text x="{wordmark_x}" y="{baseline}"
          font-family="Inter, Arial, sans-serif" font-size="{font_size}" letter-spacing="-3.2"><tspan
          fill="{main_fill}" font-weight="600">SysSim</tspan><tspan fill="{x_fill}"
          font-weight="700">X</tspan></text>'''

    background = (
        f'<rect width="{viewbox_width}" height="240" fill="{COLORS.navy}"/>'
        if palette == "dark"
        else ""
    )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {viewbox_width} 240"
  role="img" aria-label="SysSimX horizontal logo">
  {background}
  <g transform="translate(22 22) scale(0.765625)" shape-rendering="geometricPrecision" stroke-linejoin="round">
    <g fill="none" stroke="{stroke}" stroke-width="14" stroke-linecap="butt">
      <path d="M 72 72 L 121 121"/>
      <path d="M 184 72 L 135 121"/>
      <path d="M 72 184 L 121 135"/>
      <path d="M 184 184 L 135 135"/>
    </g>
    <g fill="{node_fill}" stroke="{stroke}" stroke-width="8">
      <rect x="24" y="24" width="48" height="48" rx="10"/>
      <rect x="184" y="24" width="48" height="48" rx="10"/>
      <rect x="24" y="184" width="48" height="48" rx="10"/>
      <rect x="184" y="184" width="48" height="48" rx="10"/>
    </g>
    <g fill="{port_fill}">
      <circle cx="72" cy="72" r="7"/>
      <circle cx="184" cy="72" r="7"/>
      <circle cx="72" cy="184" r="7"/>
      <circle cx="184" cy="184" r="7"/>
    </g>
  </g>
  {wordmark}
</svg>'''


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _png(svg: str, destination: Path, width: int, height: int | None = None) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    cairosvg.svg2png(
        bytestring=svg.encode("utf-8"),
        write_to=str(destination),
        output_width=width,
        output_height=height,
    )


def _write_ico(destination: Path, layers: list[tuple[int, Path]]) -> None:
    """Pack exact PNG layers into a Windows ICO without resampling them."""
    png_data = [path.read_bytes() for _, path in layers]
    directory_size = 6 + 16 * len(layers)
    offset = directory_size
    directory = [struct.pack("<HHH", 0, 1, len(layers))]
    entries: list[bytes] = []

    for (size, _), data in zip(layers, png_data, strict=True):
        dimension = 0 if size == 256 else size
        entries.append(
            struct.pack(
                "<BBBBHHII",
                dimension,
                dimension,
                0,
                0,
                1,
                32,
                len(data),
                offset,
            )
        )
        offset += len(data)

    destination.write_bytes(b"".join(directory + entries + png_data))


def build_assets(
    output_directory: Path,
    *,
    inter_semibold: Path | None = None,
    inter_bold: Path | None = None,
    create_zip: bool = False,
) -> Path:
    output_directory = output_directory.resolve()
    if output_directory.exists():
        shutil.rmtree(output_directory)

    svg_dir = output_directory / "svg"
    png_dir = output_directory / "png"
    svg_dir.mkdir(parents=True)
    png_dir.mkdir(parents=True)

    svg_assets = {
        "syssimx_icon_primary.svg": icon_svg(palette="light"),
        "syssimx_icon_dark.svg": icon_svg(palette="dark"),
        "syssimx_icon_monochrome_dark.svg": icon_svg(palette="mono_dark"),
        "syssimx_icon_monochrome_reversed.svg": icon_svg(palette="mono_light"),
        "syssimx_app_icon_solid_navy.svg": icon_svg(palette="dark", solid_background=True),
        "syssimx_icon_micro_16.svg": icon_svg(palette="light", micro_mode="16"),
        "syssimx_icon_micro_24.svg": icon_svg(palette="light", micro_mode="24"),
        "syssimx_favicon_16.svg": favicon_16_svg(),
        "syssimx_horizontal_light.svg": horizontal_svg("light", inter_semibold=inter_semibold, inter_bold=inter_bold),
        "syssimx_horizontal_dark.svg": horizontal_svg("dark", inter_semibold=inter_semibold, inter_bold=inter_bold),
        "syssimx_horizontal_monochrome.svg": horizontal_svg("mono", inter_semibold=inter_semibold, inter_bold=inter_bold),
    }

    for filename, svg in svg_assets.items():
        _write(svg_dir / filename, svg)

    for size in [16, 24, 32, 64, 128, 256, 512]:
        mode: MicroMode = "16" if size == 16 else "24" if size == 24 else None
        _png(icon_svg(palette="light", micro_mode=mode), png_dir / f"syssimx_icon_{size}px.png", size, size)

    for size in [16, 24, 32, 64, 128, 256, 512, 1024]:
        mode = "16" if size == 16 else "24" if size == 24 else None
        _png(
            icon_svg(palette="dark", solid_background=True, micro_mode=mode),
            png_dir / f"syssimx_app_icon_solid_navy_{size}px.png",
            size,
            size,
        )

    _png(favicon_16_svg(), png_dir / "syssimx_favicon_16px.png", 16, 16)

    for width in [256, 512, 1024]:
        _png(svg_assets["syssimx_horizontal_light.svg"], png_dir / f"syssimx_horizontal_light_{width}px.png", width)

    _write_ico(
        output_directory / "syssimx_favicon.ico",
        [
            (16, png_dir / "syssimx_favicon_16px.png"),
            (32, png_dir / "syssimx_app_icon_solid_navy_32px.png"),
            (64, png_dir / "syssimx_app_icon_solid_navy_64px.png"),
        ],
    )

    metadata = {
        "colors": COLORS.__dict__,
        "standard_geometry": STANDARD.__dict__,
        "micro_16_geometry": MICRO_16.__dict__,
        "micro_24_geometry": MICRO_24.__dict__,
        "wordmark_outlined": bool(inter_semibold and inter_bold),
        "inter_semibold": str(inter_semibold) if inter_semibold else None,
        "inter_bold": str(inter_bold) if inter_bold else None,
    }
    _write(output_directory / "build_info.json", json.dumps(metadata, indent=2))

    if create_zip:
        archive_path = output_directory.with_suffix(".zip")
        if archive_path.exists():
            archive_path.unlink()
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for file in output_directory.rglob("*"):
                if file.is_file():
                    archive.write(file, file.relative_to(output_directory.parent))

    return output_directory


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate SysSimX logo assets.")
    parser.add_argument("--output", type=Path, default=SPEC_PATH.parents[1] / "dist")
    parser.add_argument("--inter-semibold", type=Path)
    parser.add_argument("--inter-bold", type=Path)
    parser.add_argument("--zip", action="store_true", help="also create a sibling ZIP archive")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if bool(args.inter_semibold) != bool(args.inter_bold):
        raise SystemExit("Provide both --inter-semibold and --inter-bold, or neither.")
    build_assets(
        args.output,
        inter_semibold=args.inter_semibold,
        inter_bold=args.inter_bold,
        create_zip=args.zip,
    )
    print(f"Built SysSimX logo assets in {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
