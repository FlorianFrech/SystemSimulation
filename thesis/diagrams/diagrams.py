import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "src"
OUT_ROOT = ROOT / "out"

# Choose the formats to generate here.
# FORMATS = ["latex:nopreamble"]
FORMATS = ["pdf"]
# FORMATS = ["svg", "pdf"]
# FORMATS = ["svg", "pdf", "latex:nopreamble"]


def build_env() -> dict[str, str]:
    env = os.environ.copy()
    existing = env.get("JAVA_TOOL_OPTIONS", "").strip()
    headless = "-Djava.awt.headless=true"
    env["JAVA_TOOL_OPTIONS"] = f"{existing} {headless}".strip()
    return env


def should_render(puml_file: Path) -> bool:
    rel = puml_file.relative_to(SRC_DIR)

    # Shared include/theme fragments are not standalone diagrams.
    if "includes" in rel.parts:
        return False

    return True


def render_diagram(puml_file: Path, fmt: str, env: dict[str, str]) -> None:
    rel_parent = puml_file.relative_to(SRC_DIR).parent
    fmt_name = fmt.split(":")[0]
    out_dir = OUT_ROOT / fmt_name / rel_parent
    out_dir.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        [
            "plantuml",
            f"-t{fmt}",
            str(puml_file),
            "-o",
            str(out_dir.resolve()),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        sys.stderr.write(result.stdout)
        raise subprocess.CalledProcessError(
            result.returncode,
            result.args,
            output=result.stdout,
            stderr=result.stderr,
        )


def main() -> int:
    if not SRC_DIR.exists():
        raise FileNotFoundError(f"Diagram source directory does not exist: {SRC_DIR}")

    src_files = sorted(p for p in SRC_DIR.rglob("*.puml") if should_render(p))
    if not src_files:
        raise RuntimeError(f"No renderable .puml files found below {SRC_DIR}")

    env = build_env()

    total_jobs = len(src_files) * len(FORMATS)
    job_index = 0

    for puml_file in src_files:
        rel_path = puml_file.relative_to(ROOT)
        for fmt in FORMATS:
            job_index += 1
            print(f"[{job_index}/{total_jobs}] {fmt}: {rel_path}")
            render_diagram(puml_file, fmt, env)

    print(f"Rendered {len(src_files)} diagram sources to {OUT_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
