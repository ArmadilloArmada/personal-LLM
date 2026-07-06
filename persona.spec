# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — Windows portable Persona.exe (one-folder build)."""

from pathlib import Path
import os

from PyInstaller.utils.hooks import collect_submodules

root = Path(SPECPATH)
src_static = root / "src" / "persona" / "web" / "static"

hiddenimports = collect_submodules("uvicorn")
hiddenimports += collect_submodules("fastapi")
hiddenimports += collect_submodules("starlette")
hiddenimports += collect_submodules("pydantic")
hiddenimports += collect_submodules("pydantic_settings")
hiddenimports += collect_submodules("httpx")
hiddenimports += [
    "persona",
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
    "yaml",
    "multipart",
    "anyio",
    "anyio._backends._asyncio",
    "sniffio",
    "h11",
    "httpcore",
    "certifi",
]

a = Analysis(
    [str(root / "persona_exe.py")],
    pathex=[str(root / "src")],
    binaries=[],
    datas=[(str(src_static), "persona" + os.sep + "web" + os.sep + "static")],
    hiddenimports=hiddenimports,
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
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Persona",
)
