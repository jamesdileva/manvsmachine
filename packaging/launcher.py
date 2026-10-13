"""Executable entry point: boot the app and open the browser.

Used as PyInstaller's entry script (see packaging/manvsmachine.spec), and
runnable directly from the repo:

    python packaging/launcher.py

In a frozen build the bundled frontend lives beside the unpacked distribution,
so the static directory is pointed at it explicitly. Everything else —
SQLite, the challenge library, and the Alembic migrations that run on startup —
comes from the bundle.

The launcher never dies silently: any startup failure is written to
``manvsmachine-crash.log`` next to the executable, printed, and held on screen
so the player can report what happened.
"""

import os
import socket
import sys
import threading
import traceback
import webbrowser
from pathlib import Path

HOST = "127.0.0.1"
PORT = 8000
URL = f"http://{HOST}:{PORT}"
CRASH_LOG = "manvsmachine-crash.log"


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
    executable_dir = _executable_dir()
    os.environ.setdefault(
        "DATABASE_URL",
        f"sqlite+aiosqlite:///{(executable_dir / 'manvsmachine.db').as_posix()}",
    )


def _open_browser(url: str) -> None:
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()


def _executable_dir() -> Path:
    return Path(sys.executable).resolve().parent


def _check_bundle_intact(executable_dir: Path) -> str | None:
    """The one-dir layout needs `_internal/` beside the exe.

    The classic failure this catches is running the exe straight out of an
    unextracted zip: Windows lets you double-click inside the archive, but the
    bundled runtime is not really there.
    """
    if not getattr(sys, "frozen", False):
        return None
    if not (executable_dir / "_internal").is_dir():
        return (
            "The game files are missing: '_internal' was not found next to the\n"
            "executable. If you opened this from inside the .zip file, close it,\n"
            "extract the whole zip first (right-click > Extract All), then run\n"
            "ManVsMachine.exe from the extracted folder."
        )
    return None


def _find_free_port(first: int = PORT, tries: int = 10) -> int | None:
    """The first free port from `first` upward (double-clicking twice just works).

    Everything the UI needs is relative (`/api/v1`, and the socket URL resolves
    against the page), so any port serves the full game with zero extra config.
    """
    for port in range(first, first + tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind((HOST, port))
            except OSError:
                continue
            return port
    return None


def _check_directory_writable(directory: Path) -> str | None:
    """The save database lives beside the exe, so the folder must be writable."""
    probe = directory / ".manvsmachine-write-test"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError:
        return (
            "This folder is not writable, so the game cannot save:\n"
            f"  {directory}\n"
            "Move the ManVsMachine folder somewhere you can write to\n"
            "(e.g. Documents) and run it from there."
        )
    return None


def _preflight() -> str | None:
    """Human-readable reason the game cannot start, or None when it can."""
    if not getattr(sys, "frozen", False):
        return None
    executable_dir = _executable_dir()
    return _check_bundle_intact(executable_dir) or _check_directory_writable(
        executable_dir
    )


def _report_fatal(message: str) -> int:
    """Show a startup failure and keep it on screen; also log it to a file."""
    report = f"Man vs. Machine could not start.\n\n{message}\n"
    print(report, flush=True)
    try:
        log = _executable_dir() / CRASH_LOG if getattr(sys, "frozen", False) else Path(CRASH_LOG)
        log.write_text(report, encoding="utf-8")
        print(f"Details saved to: {log}", flush=True)
    except OSError:
        pass
    _hold_open()
    return 1


def _hold_open() -> None:
    """Keep a double-clicked console window open so the message can be read.

    The `isatty` guard alone is not enough: a hidden/redirected console can
    still claim a tty while having no readable stdin, so the read itself is
    guarded too — holding the window open must never be what crashes.
    """
    if not sys.stdin.isatty():
        return
    try:
        input("Press Enter to close...")
    except (EOFError, OSError):
        pass


def main() -> int:
    problem = _preflight()
    if problem is not None:
        return _report_fatal(problem)

    _point_at_bundled_frontend()
    _bundle_database()

    port = _find_free_port()
    if port is None:
        return _report_fatal(
            "No free port was found near 8000 — close other copies of the game\n"
            "(or other apps using those ports) and try again."
        )
    url = f"http://{HOST}:{port}"
    if port != PORT:
        print(f"Port {PORT} was busy, so the game is using port {port} instead.")

    try:
        import uvicorn

        from app.main import app
    except Exception:  # noqa: BLE001 — startup must never die silently
        return _report_fatal(
            "The game files failed to load. Re-extract the zip (or redownload it)\n"
            "and try again. Technical details:\n\n" + traceback.format_exc()
        )

    print(f"Man vs. Machine — {url}")
    print("Press Ctrl+C to stop.")

    _open_browser(url)
    try:
        uvicorn.run(app, host=HOST, port=port, log_level="info")
    except Exception:  # noqa: BLE001 — e.g. the port was taken mid-start
        return _report_fatal(
            "The server stopped unexpectedly. Technical details:\n\n"
            + traceback.format_exc()
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
