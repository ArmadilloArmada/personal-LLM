# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — builds Persona-Setup.exe (Windows one-folder app)."""

import sys
from pathlib import Path

root = Path(SPECPATH)
src = root / "src" / "persona" / "web" / "static"

a = Analysis(
    [str(root / "persona_exe.py")],
    pathex=[str(root / "src")],
    binaries=[],
    datas=[(str(src), "persona/web/static")],
    hiddenimports=[
        "persona",
        "persona.cli",
        "persona.launcher",
        "persona.demo",
        "persona.web.server",
        "persona.crew",
        "persona.agent",
        "persona.llm",
        "persona.personas",
        "persona.custom",
        "persona.rag",
        "persona.workspace",
        "persona.avatars",
        "persona.projects",
        "persona.tools",
        "persona.memory",
        "persona.models",
        "persona.config",
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
        "fastapi",
        "starlette",
        "pydantic",
        "pydantic_settings",
        "httpx",
        "yaml",
        "typer",
        "rich",
        "click",
        "multipart",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Persona",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Persona",
)
