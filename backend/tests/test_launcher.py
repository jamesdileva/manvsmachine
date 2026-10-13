"""Packaging/launcher tests (owner-approved PyInstaller bundling, §8).

The launcher's only real logic is finding the bundled frontend and keeping the
SQLite file beside the executable — both are pure path decisions, so they are
tested directly rather than by building a 40 MB artifact.
"""

import os
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
