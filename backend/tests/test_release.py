"""Release-mode static hosting tests (Sprint 27).

The single-port release mode serves the built frontend from FastAPI alongside
the API and the WebSocket. These tests pin the important behaviour: the app
shell is served for browser routes, unknown paths fall back to it (client-side
routing), and the API/docs/health routes are never shadowed by it.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import main as main_module
from app.core.config import settings
from app.main import FRONTEND_DIST_DIR

INDEX_HTML = """<!doctype html>
<html lang="en">
  <head><title>Man vs. Machine</title></head>
  <body><div id="root"></div><script src="/assets/index-abc.js"></script></body>
</html>
"""


@pytest.fixture
def built_frontend(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """The app pointed at a fake `frontend/dist` build output."""
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    (dist / "assets" / "index-abc.js").write_text("console.log('app')", encoding="utf-8")
    (dist / "vite.svg").write_text("<svg></svg>", encoding="utf-8")
    monkeypatch.setattr(main_module, "FRONTEND_DIST_DIR", dist)

    db_file = tmp_path / "release.db"
    monkeypatch.setattr(
        settings, "database_url", f"sqlite+aiosqlite:///{db_file.as_posix()}"
    )
    from app import main

    with TestClient(main.app) as client:
        yield client


@pytest.fixture
def no_build(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Dev mode: no build output present, so nothing is mounted."""
    monkeypatch.setattr(main_module, "FRONTEND_DIST_DIR", tmp_path / "missing-dist")
    db_file = tmp_path / "release.db"
    monkeypatch.setattr(
        settings, "database_url", f"sqlite+aiosqlite:///{db_file.as_posix()}"
    )
    from app import main

    with TestClient(main.app) as client:
        yield client


# ---------------------------------------------------------------------------
# Release mode: the build output is served


def test_root_serves_the_built_frontend(built_frontend: TestClient) -> None:
    response = built_frontend.get("/")
    assert response.status_code == 200, response.text
    assert "text/html" in response.headers["content-type"]
    assert "Man vs. Machine" in response.text


def test_hashed_assets_are_served(built_frontend: TestClient) -> None:
    response = built_frontend.get("/assets/index-abc.js")
    assert response.status_code == 200
    assert "console.log('app')" in response.text


def test_other_build_files_are_served(built_frontend: TestClient) -> None:
    assert built_frontend.get("/vite.svg").status_code == 200


def test_unknown_browser_path_falls_back_to_the_shell(built_frontend: TestClient) -> None:
    """Client-side routes (/profile, /session) must serve index.html, not 404."""
    for path in ("/profile", "/session", "/some/deep/route"):
        response = built_frontend.get(path)
        assert response.status_code == 200, path
        assert "Man vs. Machine" in response.text


def test_missing_asset_is_404_not_the_shell(built_frontend: TestClient) -> None:
    assert built_frontend.get("/assets/does-not-exist.js").status_code == 404


def test_the_api_is_never_shadowed_by_the_fallback(built_frontend: TestClient) -> None:
    """An unknown API path must return the API's JSON 404, not the HTML shell."""
    response = built_frontend.get("/api/v1/definitely-not-a-route")
    assert response.status_code == 404
    assert "json" in response.headers["content-type"]
    assert "<html" not in response.text


def test_websocket_route_is_not_shadowed(built_frontend: TestClient) -> None:
    """The WS upgrade path stays the server's; the fallback must not claim it."""
    with (
        pytest.raises(Exception),  # noqa: B017 - a rejected handshake, not HTML
        built_frontend.websocket_connect("/ws/session/nope?token=bad"),
    ):
        pass


def test_docs_and_health_still_work(built_frontend: TestClient) -> None:
    assert built_frontend.get("/health").status_code == 200
    assert built_frontend.get("/openapi.json").status_code == 200
    assert built_frontend.get("/docs").status_code == 200


# ---------------------------------------------------------------------------
# Dev mode: no build output


def test_root_is_404_without_a_build(no_build: TestClient) -> None:
    response = no_build.get("/")
    assert response.status_code == 404
    assert "<html" not in response.text


def test_the_api_works_without_a_build(no_build: TestClient) -> None:
    assert no_build.get("/health").status_code == 200


def test_frontend_dist_dir_points_at_the_vite_output() -> None:
    assert FRONTEND_DIST_DIR == (
        Path(__file__).resolve().parents[2] / "frontend" / "dist"
    )
