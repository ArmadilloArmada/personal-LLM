#!/usr/bin/env python3
"""Record the Persona interactive demo as an MP4 using Playwright."""

from __future__ import annotations

import http.server
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "demo"
OUT_DIR = Path("/opt/cursor/artifacts/videos")
OUT_MP4 = OUT_DIR / "Persona-demo.mp4"
OUT_WEBM = OUT_DIR / "Persona-demo.webm"


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def serve_demo(port: int) -> http.server.HTTPServer:
    handler = http.server.SimpleHTTPRequestHandler

    class QuietHandler(handler):
        def log_message(self, format: str, *args) -> None:
            pass

    import os

    os.chdir(DEMO_DIR)
    server = http.server.HTTPServer(("127.0.0.1", port), QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def record() -> Path:
    from playwright.sync_api import sync_playwright

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    port = find_free_port()
    server = serve_demo(port)
    url = f"http://127.0.0.1:{port}/index.html?record=1"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                record_video_dir=str(OUT_DIR),
                record_video_size={"width": 1280, "height": 720},
            )
            page = context.new_page()
            page.goto(url, wait_until="networkidle")
            page.wait_for_selector('[data-demo-complete="1"]', timeout=180_000)
            time.sleep(5)
            page.close()
            context.close()
            browser.close()

        webms = sorted(OUT_DIR.glob("*.webm"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not webms:
            raise RuntimeError("No webm recording produced")
        raw = webms[0]
        shutil.move(str(raw), str(OUT_WEBM))

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(OUT_WEBM),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(OUT_MP4),
            ],
            check=True,
            capture_output=True,
        )
        return OUT_MP4
    finally:
        server.shutdown()


if __name__ == "__main__":
    try:
        path = record()
        print(f"Wrote {path} ({path.stat().st_size // 1024} KB)")
    except Exception as exc:
        print(f"Recording failed: {exc}", file=sys.stderr)
        sys.exit(1)
