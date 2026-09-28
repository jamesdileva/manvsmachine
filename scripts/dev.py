"""One-command local dev: starts the backend (uvicorn) and frontend (Vite) together.

Usage (from the project root, with the project venv active):

    python scripts/dev.py

No Docker required. The backend serves http://127.0.0.1:8000 (API + Swagger at /docs),
the frontend dev server serves http://localhost:5173. Ctrl+C stops both.
"""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"

BACKEND_URL = "http://127.0.0.1:8000"
FRONTEND_URL = "http://localhost:5173"


def main() -> int:
    """Launch both dev servers and block until one exits or Ctrl+C is received."""
    npm = shutil.which("npm")
    if npm is None:
        print("error: npm not found on PATH — install Node.js 18+ first", file=sys.stderr)
        return 1
    if not (BACKEND_DIR / "app" / "main.py").exists():
        print(f"error: backend not found at {BACKEND_DIR}", file=sys.stderr)
        return 1
    if not (FRONTEND_DIR / "package.json").exists():
        print(
            f"error: frontend not found at {FRONTEND_DIR} — run `npm install` in frontend/",
            file=sys.stderr,
        )
        return 1

    procs: list[subprocess.Popen[bytes]] = []
    try:
        backend = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--reload",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ],
            cwd=BACKEND_DIR,
            env=os.environ.copy(),
        )
        procs.append(backend)
        frontend = subprocess.Popen([npm, "run", "dev"], cwd=FRONTEND_DIR, env=os.environ.copy())
        procs.append(frontend)

        print(f"backend  : {BACKEND_URL}  (Swagger UI at {BACKEND_URL}/docs)")
        print(f"frontend : {FRONTEND_URL}")
        print("press Ctrl+C to stop both servers")

        while True:
            for proc in procs:
                code = proc.poll()
                if code is not None:
                    # One server died — stop the other and propagate the exit code.
                    print(f"\na dev server exited with code {code}; shutting down", file=sys.stderr)
                    return code
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nshutting down dev servers...")
        return 0
    finally:
        for proc in procs:
            if proc.poll() is None:
                proc.terminate()
        for proc in procs:
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
