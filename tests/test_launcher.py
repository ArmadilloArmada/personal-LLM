"""Tests for standalone launcher helpers."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from persona import launcher


def test_frozen_windows_detection(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert launcher._frozen_windows() is False

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "linux", raising=False)
    assert launcher._frozen_windows() is False

    monkeypatch.setattr(sys, "platform", "win32", raising=False)
    assert launcher._frozen_windows() is True


def test_open_window_prefers_edge_on_frozen_windows(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "win32", raising=False)

    with (
        patch.object(launcher, "_open_browser_app_mode", return_value=True) as edge,
        patch.object(launcher, "_try_pywebview") as webview,
        patch.object(launcher, "_keepalive") as keepalive,
    ):
        launcher._open_window("http://127.0.0.1:8765")

    edge.assert_called_once_with("http://127.0.0.1:8765")
    webview.assert_not_called()
    keepalive.assert_called_once()


def test_open_window_pywebview_then_browser_fallback(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)

    with (
        patch.object(launcher, "_try_pywebview", return_value=False),
        patch.object(launcher, "_open_browser_app_mode", return_value=False),
        patch("persona.launcher.webbrowser.open") as browser_open,
        patch.object(launcher, "_keepalive") as keepalive,
    ):
        launcher._open_window("http://127.0.0.1:8765")

    browser_open.assert_called_once_with("http://127.0.0.1:8765")
    keepalive.assert_called_once()


def test_try_pywebview_fast_exit_on_frozen_windows(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "win32", raising=False)

    fake_webview = MagicMock()
    monkeypatch.setitem(sys.modules, "webview", fake_webview)

    with patch.object(launcher.time, "time", side_effect=[0.0, 0.5]):
        assert launcher._try_pywebview("http://127.0.0.1:8765") is False

    fake_webview.create_window.assert_called_once()
    fake_webview.start.assert_called_once_with(gui="edgechromium")
