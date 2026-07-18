# SysSimX Logo Production Specification

## Master geometry
- Coordinate system: 256 × 256 units.
- Component nodes: 48 × 48 units, corner radius 10 units.
- Node positions: (24,24), (184,24), (24,184), and (184,184).
- Connector centerlines: (72,72)–(184,184) and (184,72)–(72,184).
- Standard connector stroke: 14 units, butt caps and round joins.
- Standard node outline: 8 units.
- Port radius: 7 units.
- Central negative-space diamond: vertices (128,114), (142,128), (128,142), and (114,128).
- The symbol uses four butt-ended diagonal arms whose inner caps lie exactly on the four edges of a centered negative-space diamond. This avoids renderer-dependent masks while preserving the appearance of one intentional X.

## 16 px favicon master
- Preferred file: `syssimx_favicon_16.svg` on a solid navy background.
- A transparent micro master is also included as `syssimx_icon_micro_16.svg`, but the solid pixel-hinted asset is the production recommendation.
- Component nodes: 56 × 56 units, corner radius 13 units.
- Connector stroke: 24 units.
- Node outline: 18 units.
- Port radius: 14 units.
- Central diamond half-diagonal: 20 units.
- The favicon master uses a native 16 × 16 coordinate system and pixel-aligned geometry.
- Use it for browser favicons and other exact 16 px contexts.

## 24 px optical master
- File: `syssimx_icon_micro_24.svg`.
- Component nodes: 54 × 54 units, corner radius 12 units.
- Connector stroke: 20 units.
- Node outline: 14 units.
- Port radius: 12 units.
- Central diamond half-diagonal: 17 units.
- Use only for 24 px UI rendering.

## Colors
- SysSimX Navy: `#10243E`
- Electric Cyan: `#00BFE8`
- White: `#FFFFFF`
- Monochrome ink: `#111827`

## Wordmark
- Typeface: Inter.
- “SysSim”: Inter SemiBold (600).
- Final “X”: Inter Bold (700).
- Release horizontal SVGs should contain outlined glyphs, so rendering does not depend on a locally installed font. The builder produces those when both Inter font files are supplied; otherwise it emits live SVG text with an Inter fallback.
- The final X uses Electric Cyan in the two-color versions.

## Clear space
- Define `N` as the standard component-node width: 48 units.
- Minimum external clear space: `0.5N` on every side.
- Minimum icon-to-wordmark spacing: `0.67N`.
- No text, border, or competing mark may enter this zone.

## Minimum sizes
- Standard icon master: 32 px digital or 8 mm print.
- 16 px and 24 px: use the corresponding optical master; never scale down the standard master.
- Horizontal lockup: 140 px digital or 30 mm print.
- At 16 px, use `dist/svg/syssimx_favicon_16.svg`, `dist/png/syssimx_favicon_16px.png`, or the supplied multi-resolution ICO.

## App icon
- Production app icon: solid SysSimX Navy background with white geometry and cyan ports.
- Canvas ratio: 1:1.
- Outer background radius: 52 units on the 256-unit canvas.
- Platform masks may crop the outer background; preserve the supplied internal margins.

## Validation evidence
- The actual SVG masters were rasterized to 16, 24, 32, and 64 px.
- The exact exported PNG files were enlarged with nearest-neighbor resampling for pixel-grid inspection.
- A multi-resolution ICO containing 16, 32, and 64 px assets was generated.
- Browser-tab, solid app-icon, and monochrome preflight contexts are shown in `validation/syssimx_validation_sheet.png`.
- Raster measurements are recorded in `validation/raster_validation.json`.
- Physical print validation cannot be completed digitally. Produce laser and inkjet proofs at 8 mm and 15 mm before release.

## Source of truth
- Human-readable rules: this document.
- Machine-readable colors and geometry: `spec/logo_spec.json`.
- Asset generation: `tools/build_logo_assets.py`.
- Generated deliverables: `dist/`; do not edit these files manually.
