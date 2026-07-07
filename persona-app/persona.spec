# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — Windows portable Persona.exe with Big Brain."""

from pathlib import Path

root = Path(SPECPATH)
src = root / "src" / "persona" / "web" / "static"
brain_root = root.parent / "big-brain"

datas = [(str(src), "persona/web/static")]

brain_client = brain_root / "client" / "dist"
brain_server = brain_root / "server" / "dist"
if brain_client.exists():
    datas.append((str(brain_client), "brain/client/dist"))
if brain_server.exists():
    datas.append((str(brain_server), "brain/server/dist"))

a = Analysis(
    [str(root / "persona_exe.py")],
    pathex=[str(root / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "persona",
        "persona.launcher",
        "persona.instance",
        "persona.tray",
        "persona.browser",
        "persona.dialogs",
        "persona.big_brain",
        "persona.big_brain.client",
        "persona.big_brain.process",
        "persona.big_brain.paths",
        "persona.web.brain_routes",
        "persona.providers",
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
        "pystray",
        "PIL",
        "PIL.Image",
        "PIL.ImageDraw",
        "pythonnet",
        "clr_loader",
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
