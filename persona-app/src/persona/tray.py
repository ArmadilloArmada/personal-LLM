"""Windows system tray for Persona portable builds."""

from __future__ import annotations

import os
import sys
import threading
import time
import webbrowser
from typing import Callable

_shutdown: Callable[[], None] | None = None
_app_url: str = ""


def run_tray(url: str, on_quit: Callable[[], None]) -> None:
    """Block until the user quits from the tray menu."""
    global _shutdown, _app_url
    _shutdown = on_quit
    _app_url = url

    if sys.platform != "win32":
        _console_keepalive()
        return

    try:
        import pystray
        from PIL import Image, ImageDraw
    except ImportError:
        _console_keepalive()
        return

    icon_image = _make_icon_image()
    menu = pystray.Menu(
        pystray.MenuItem("Open Persona", _menu_open, default=True),
        pystray.MenuItem("Restart window", _menu_restart),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", _menu_quit),
    )
    icon = pystray.Icon("Persona", icon_image, f"Persona — {url}", menu)
    icon.run()


def _make_icon_image():
    from PIL import Image, ImageDraw

    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((4, 4, 60, 60), radius=12, fill=(99, 102, 241, 255))
    draw.text((22, 16), "P", fill=(255, 255, 255, 255))
    return img


def _menu_open(icon, _item) -> None:
    from persona.browser import open_persona_ui

    open_persona_ui(_app_url)


def _menu_restart(icon, _item) -> None:
    from persona.browser import open_persona_ui

    open_persona_ui(_app_url, force_new=True)


def _menu_quit(icon, _item) -> None:
    icon.stop()
    if _shutdown:
        _shutdown()
    os._exit(0)


def _console_keepalive() -> None:
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        if _shutdown:
            _shutdown()
