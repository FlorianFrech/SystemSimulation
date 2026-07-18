# SysSimX logo assets

This directory is a self-contained asset workspace for the SysSimX brand. It is
not an installable Python project and intentionally has no `pyproject.toml`.
The main repository remains the only Python project.

## Layout

```text
logo/
├── BRAND_SPEC.md                 # human-readable brand rules
├── requirements.txt              # optional builder/test dependencies
├── pytest.ini                    # logo-workspace test configuration
├── spec/logo_spec.json           # machine-readable source of truth
├── tools/build_logo_assets.py    # reproducible asset builder
├── tests/                        # builder and geometry tests
├── dist/                         # canonical generated deliverables
│   ├── svg/
│   ├── png/
│   ├── syssimx_favicon.ico
│   └── build_info.json            # produced by the builder for new builds
├── validation/                   # raster preflight evidence
└── archive/                      # historical/example packages only
```

The canonical source files are the builder and `spec/logo_spec.json`. The
contents of `dist/` are generated outputs and should not be edited manually.
The preserved release exports may predate `build_info.json`; it is created on
the next successful build.

## Install builder dependencies

From this directory:

```bash
python -m pip install -r requirements.txt
```

CairoSVG may require a system Cairo installation. On Ubuntu/Debian:

```bash
sudo apt-get install libcairo2
```

## Build assets

From this directory:

```bash
python tools/build_logo_assets.py
```

The default output is `dist/`. To write a package archive as well:

```bash
python tools/build_logo_assets.py --zip
```

For self-contained horizontal SVGs with outlined Inter glyphs, provide matching
Inter SemiBold and Inter Bold font files:

```bash
python tools/build_logo_assets.py \
  --inter-semibold /path/to/Inter-SemiBold.ttf \
  --inter-bold /path/to/Inter-Bold.ttf
```

Without font arguments, the builder uses live SVG text with an Inter fallback.
The supplied release SVGs may contain outlined glyphs from a prior font-backed
build; `dist/build_info.json` records which mode was used for a generated set.

## Test the builder

```bash
python -m pytest tests -q
```

## Using the assets

- Light background: `dist/svg/syssimx_horizontal_light.svg` and
  `dist/svg/syssimx_icon_primary.svg`
- Dark background: `dist/svg/syssimx_horizontal_dark.svg` and
  `dist/svg/syssimx_icon_dark.svg`
- GitHub/social preview: `dist/png/syssimx_social_preview_1280x640.png`
  with its vector source in `dist/svg/syssimx_social_preview.svg`
- Browser favicon: `dist/svg/syssimx_favicon_16.svg` or
  `dist/syssimx_favicon.ico`
- Solid application icon: `dist/svg/syssimx_app_icon_solid_navy.svg`
- Monochrome/print: the monochrome SVG variants

Use `validation/syssimx_validation_sheet.png` for a visual preflight. Physical
proofs at the documented minimum print sizes are still required before final
print release.
