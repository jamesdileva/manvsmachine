"""Executable entry point: boot the app and open the browser.

Used as PyInstaller's entry script (see packaging/manvsmachine.spec), and
runnable directly from the repo:

    python packaging/launcher.py

In a frozen build the bundled frontend lives beside the unpacked distribution,
so the static directory is pointed at it explicitly. Everything else —
SQLite, the challenge library, and the Alembic migrations that run on startup —
comes from the bundle.
"""

import os
import sys
import threading
import webbrowser
from pathlib import Path

HOST = "127.0.0.1"
PORT = 8000
URL = f"http://{HOST}:{PORT}"


def _bundle_root() -> Path | None:
    """The PyInstaller unpack directory, or None when running from source."""
    if getattr(sys, "frozen", False) is not True:
        return None
    return Path(getattr(sys, "_MEIPASS", "") or Path(sys.executable).parent)


def _point_at_bundled_frontend() -> None:
    """Make the app serve the frontend that ships inside the bundle.

    PyInstaller's one-dir layout puts collected data under `_internal/`, while a
    one-file build unpacks to the temp `_MEIPASS` root — so both are checked.
    """
    if getattr(sys, "frozen", False) is not True:
        return
    if os.environ.get("MANVSMACHINE_FRONTEND_DIST"):
        return

    roots = [Path(getattr(sys, "_MEIPASS", "") or Path(sys.executable).parent)]
    roots.append(Path(sys.executable).resolve().parent)
    for root in {r for r in roots if str(r)}:
        for relative in ("frontend/dist", "_internal/frontend/dist"):
            bundled = root / relative
            if (bundled / "index.html").is_file():
                os.environ["MANVSMACHINE_FRONTEND_DIST"] = str(bundled)
                return


def _bundle_database() -> None:
    """Keep the player's SQLite file next to the executable, not in the temp dir.

    A one-file build unpacks into a per-run temp directory, so persisting the
    database there would wipe every session on each launch.
    """
    if not getattr(sys, "frozen", False):
        return
    executable_dir = Path(sys.executable).resolve().parent
    os.environ.setdefault(
        "DATABASE_URL",
        f"sqlite+aiosqlite:///{(executable_dir / 'manvsmachine.db').as_posix()}",
    )


def _open_browser() -> None:
    threading.Timer(1.5, lambda: webbrowser.open(URL)).start()


def main() -> int:
    _point_at_bundled_frontend()
    _bundle_database()

    import uvicorn

    from app.main import app

    print(f"Man vs. Machine — {URL}")
    print("Press Ctrl+C to stop.")

    _open_browser()
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
