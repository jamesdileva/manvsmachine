"""Build the Man vs. Machine desktop bundle (PyInstaller).

Usage (from the project root, with the project venv active):

    python scripts/build_executable.py             # build (uses the existing dist/)
    python scripts/build_executable.py --rebuild-ui # rebuild the frontend first

The output is a self-contained folder you can zip and hand to anyone:

    dist/ManVsMachine/ManVsMachine(.exe)     <- double-click to play
    dist/ManVsMachine/_internal/               runtime + bundled data

No Python and no Node are needed on the target machine — the SQLite database,
the 25-challenge library, the Alembic migrations, and the built UI are all
inside the bundle. The database itself is written next to the executable on
first run, so progress survives restarts and upgrades.

PyInstaller is an owner-approved addition (Master Architecture §8; see §22
changelog v1.24). It lives in the `package` extra:

    pip install -e "backend[package]"
"""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
DIST = ROOT / "dist"


def _run(command: list[str], cwd: Path) -> None:
    print(f"$ {' '.join(command)}")
    subprocess.run(command, cwd=cwd, check=True)


def _npm() -> str:
    found = shutil.which("npm")
    if found is None:
        sys.exit("error: npm not found on PATH — install Node.js 18+ first")
    return found


def _frontend_built() -> bool:
    return (FRONTEND / "dist" / "index.html").is_file()


def _build_ui() -> None:
    if not (FRONTEND / "node_modules").is_dir():
        sys.exit("error: frontend deps missing — run `npm install` in frontend/ first")
    _run([_npm(), "run", "build"], FRONTEND)


def main() -> int:
    rebuild_ui = "--rebuild-ui" in sys.argv
    if rebuild_ui or not _frontend_built():
        if not rebuild_ui:
            print("no frontend build found — building it first")
        _build_ui()
    else:
        print("using the existing frontend build (pass --rebuild-ui to refresh it)")

    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        sys.exit(
            "error: PyInstaller is not installed.\n"
            '       install it with: pip install -e "backend[package]"'
        )

    _run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            str(ROOT / "packaging" / "manvsmachine.spec"),
            "--noconfirm",
            "--clean",
        ],
        ROOT,
    )

    output = DIST / "ManVsMachine"
    if not output.is_dir():
        sys.exit(f"error: expected {output} after the build")

    executable = output / ("ManVsMachine.exe" if sys.platform == "win32" else "ManVsMachine")
    size_mb = sum(f.stat().st_size for f in output.rglob("*") if f.is_file()) / 1e6
    print()
    print(f"built {output}  ({size_mb:.0f} MB)")
    print(f"run it:  {executable}")
    if shutil.which("zip"):
        print("zip it:  right-click dist/ManVsMachine → Send to → Compressed folder")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
