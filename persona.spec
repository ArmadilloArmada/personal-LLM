# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — Windows portable Persona.exe (one-folder build)."""

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
        "persona.launcher",
        "persona.providers",
        "persona.bundled",
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
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "uvicorn.server",
        "uvicorn.config",
        "fastapi",
        "starlette",
        "starlette.routing",
        "pydantic",
        "pydantic_core",
        "pydantic_settings",
        "annotated_types",
        "httpx",
        "httpcore",
        "h11",
        "anyio",
        "anyio._backends._asyncio",
        "sniffio",
        "certifi",
        "yaml",
        "multipart",
        "webview",
        "webview.platforms",
        "webview.platforms.edgechromium",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"],
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
