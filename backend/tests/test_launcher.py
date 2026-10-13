"""Packaging/launcher tests (owner-approved PyInstaller bundling, §8).

The launcher's only real logic is finding the bundled frontend and keeping the
SQLite file beside the executable — both are pure path decisions, so they are
tested directly rather than by building a 40 MB artifact.
"""

import os
import socket
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

PACKAGING_DIR = Path(__file__).resolve().parents[2] / "packaging"
sys.path.insert(0, str(PACKAGING_DIR))

import launcher


@pytest.fixture(autouse=True)
def _clean_env() -> Iterator[None]:
    saved = os.environ.get("MANVSMACHINE_FRONTEND_DIST")
    os.environ.pop("MANVSMACHINE_FRONTEND_DIST", None)
    yield
    if saved is None:
        os.environ.pop("MANVSMACHINE_FRONTEND_DIST", None)
    else:
        os.environ["MANVSMACHINE_FRONTEND_DIST"] = saved


def _frozen(monkeypatch: pytest.MonkeyPatch, meipass: Path, executable: Path) -> None:
    monkeypatch.setattr(launcher.sys, "frozen", True, raising=False)
    monkeypatch.setattr(launcher.sys, "_MEIPASS", str(meipass), raising=False)
    monkeypatch.setattr(launcher.sys, "executable", str(executable), raising=False)


def test_source_runs_change_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Not frozen (running from the repo): the app uses its repo-relative default."""
    _frozen(monkeypatch, tmp_path, tmp_path / "python")
    monkeypatch.setattr(launcher.sys, "frozen", False, raising=False)

    launcher._point_at_bundled_frontend()
    assert "MANVSMACHINE_FRONTEND_DIST" not in os.environ
    assert launcher._bundle_root() is None


def test_dist_beside_the_executable_is_used(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    bundle = tmp_path / "bundle"
    (bundle / "frontend" / "dist").mkdir(parents=True)
    (bundle / "frontend" / "dist" / "index.html").write_text("<html/>", encoding="utf-8")
    _frozen(monkeypatch, tmp_path / "unpack", bundle / "ManVsMachine.exe")

    launcher._point_at_bundled_frontend()

    assert os.environ["MANVSMACHINE_FRONTEND_DIST"] == str(bundle / "frontend" / "dist")


def test_internal_dist_is_used(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """PyInstaller's one-dir layout puts data under `_internal/`."""
    bundle = tmp_path / "bundle"
    (bundle / "_internal" / "frontend" / "dist").mkdir(parents=True)
    (bundle / "_internal" / "frontend" / "dist" / "index.html").write_text(
        "<html/>", encoding="utf-8"
    )
    _frozen(monkeypatch, tmp_path / "unpack", bundle / "ManVsMachine.exe")

    launcher._point_at_bundled_frontend()

    assert os.environ["MANVSMACHINE_FRONTEND_DIST"] == str(
        bundle / "_internal" / "frontend" / "dist"
    )


def test_an_existing_override_wins(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """An explicit setting (a custom install) is never overwritten."""
    os.environ["MANVSMACHINE_FRONTEND_DIST"] = "/somewhere/else"
    _frozen(monkeypatch, tmp_path, tmp_path / "ManVsMachine.exe")

    launcher._point_at_bundled_frontend()

    assert os.environ["MANVSMACHINE_FRONTEND_DIST"] == "/somewhere/else"


def test_no_bundled_frontend_sets_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A bundle without a UI build still boots — the API just 404s on `/`."""
    _frozen(monkeypatch, tmp_path, tmp_path / "ManVsMachine.exe")
    launcher._point_at_bundled_frontend()
    assert "MANVSMACHINE_FRONTEND_DIST" not in os.environ


def test_database_lives_next_to_the_executable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _frozen(monkeypatch, tmp_path, tmp_path / "ManVsMachine.exe")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    launcher._bundle_database()

    assert os.environ["DATABASE_URL"] == (
        f"sqlite+aiosqlite:///{(tmp_path / 'manvsmachine.db').as_posix()}"
    )


def test_an_existing_database_setting_is_kept(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _frozen(monkeypatch, tmp_path, tmp_path / "ManVsMachine.exe")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///custom.db")

    launcher._bundle_database()

    assert os.environ["DATABASE_URL"] == "sqlite+aiosqlite:///custom.db"


def test_bundle_root_is_none_from_source(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(launcher.sys, "frozen", False, raising=False)
    assert launcher._bundle_root() is None


# ---------------------------------------------------------------------------
# Startup preflight (the "flashes and closes" fix)


def _frozen_in(directory: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    executable = directory / "ManVsMachine.exe"
    monkeypatch.setattr(launcher.sys, "frozen", True, raising=False)
    monkeypatch.delattr(launcher.sys, "_MEIPASS", raising=False)
    monkeypatch.setattr(launcher.sys, "executable", str(executable), raising=False)


def test_preflight_is_quiet_from_source(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(launcher.sys, "frozen", False, raising=False)
    assert launcher._preflight() is None


def test_preflight_passes_for_an_intact_bundle(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "_internal").mkdir()
    _frozen_in(tmp_path, monkeypatch)
    assert launcher._preflight() is None


def test_preflight_catches_a_missing_internal_folder(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Running the exe from inside an unextracted zip: no _internal beside it."""
    _frozen_in(tmp_path, monkeypatch)
    problem = launcher._preflight()
    assert problem is not None
    assert "_internal" in problem
    assert "Extract All" in problem


def test_preflight_catches_an_occupied_port(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "_internal").mkdir()
    _frozen_in(tmp_path, monkeypatch)
    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    blocker.bind((launcher.HOST, launcher.PORT))
    try:
        problem = launcher._preflight()
    finally:
        blocker.close()
    assert problem is not None
    assert "already in use" in problem


def test_preflight_catches_an_unwritable_folder(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "_internal").mkdir()
    _frozen_in(tmp_path, monkeypatch)
    monkeypatch.setattr(
        launcher.Path, "write_text", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("denied"))
    )
    problem = launcher._preflight()
    assert problem is not None
    assert "not writable" in problem


def test_preflight_checks_in_order_intact_then_port_then_writable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A missing _internal is reported even when the port is also taken."""
    _frozen_in(tmp_path, monkeypatch)  # no _internal here
    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    blocker.bind((launcher.HOST, launcher.PORT))
    try:
        problem = launcher._preflight()
    finally:
        blocker.close()
    assert problem is not None
    assert "_internal" in problem


def test_fatal_report_returns_nonzero_and_mentions_the_log(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _frozen_in(tmp_path, monkeypatch)
    monkeypatch.setattr(launcher.sys.stdin, "isatty", lambda: False)

    code = launcher._report_fatal("something broke")

    assert code == 1
    assert "something broke" in capsys.readouterr().out
    assert (tmp_path / launcher.CRASH_LOG).is_file()


def test_hold_open_asks_when_interactive(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(launcher.sys.stdin, "isatty", lambda: True)
    asked = []
    monkeypatch.setattr("builtins.input", lambda prompt="": asked.append(prompt))

    launcher._hold_open()

    assert asked == ["Press Enter to close..."]


def test_hold_open_survives_a_dead_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    """A hidden/redirected console can claim a tty with no readable stdin."""

    class DeadStdin:
        def isatty(self) -> bool:
            return True

    monkeypatch.setattr(launcher.sys, "stdin", DeadStdin())

    def boom(prompt: str = "") -> str:
        raise EOFError

    monkeypatch.setattr("builtins.input", boom)

    launcher._hold_open()  # must not raise


def test_hold_open_stays_quiet_without_a_tty(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(launcher.sys.stdin, "isatty", lambda: False)
    launcher._hold_open()
    assert capsys.readouterr().out == ""
