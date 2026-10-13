# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build for the Man vs. Machine desktop bundle.

    python -m PyInstaller packaging/manvsmachine.spec --noconfirm --clean

Produces dist/ManVsMachine/ — a folder that runs with no Python and no Node.
`scripts/build_executable.py` wraps this (and builds the frontend first if
needed); use that unless you are hand-tuning the spec.

Data that must live on disk at runtime:
  alembic.ini + alembic/     migrations run on every startup (init_db)
  app/data/                  25 challenge JSONs, 25 stub pools, prompt template
  frontend/dist/             the built UI, served by the app itself

Destination paths mirror what the code computes from `__file__`: inside a
frozen build `app/services/challenge_service.py` resolves to
`<bundle>/app/services/...`, so the library is collected to `app/data/`.
"""

from pathlib import Path

# SPECPATH is the directory holding this spec.
_SPEC_DIR = Path(SPECPATH).resolve()
if _SPEC_DIR.is_file():
    _SPEC_DIR = _SPEC_DIR.parent

ROOT = _SPEC_DIR.parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"

datas = [
    (str(BACKEND / "alembic.ini"), "."),
    (str(BACKEND / "alembic"), "alembic"),
    (str(BACKEND / "app" / "data"), "app/data"),
    (str(FRONTEND / "dist"), "frontend/dist"),
]

# uvicorn's loops/protocols are imported lazily by string; websockets is the
# WebSocket server; alembic's env is loaded as a module, not discovered.
hiddenimports = [
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "websockets",
    "websockets.legacy",
    "websockets.legacy.server",
    "alembic",
    "alembic.config",
    "alembic.runtime",
    "alembic.runtime.migration",
    "alembic.script",
    "aiosqlite",
    "sqlmodel",
    "jwt",
    "pydantic",
    "pydantic_settings",
    "email_validator",
]

# Only what the runtime actually imports from these packages.
excludes = [
    "tkinter",
    "matplotlib",
    "numpy",
    "pandas",
    "IPython",
    "pytest",
    "mypy",
    "ruff",
]

block_cipher = None


a = Analysis(
    [str(Path(SPECPATH).resolve() / "launcher.py")],
    pathex=[str(BACKEND)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ManVsMachine",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_load_mzmagic=False,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ManVsMachine",
)
