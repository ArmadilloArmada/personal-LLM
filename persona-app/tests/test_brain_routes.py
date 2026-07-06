"""Tests for Big Brain integration routes."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from persona.web.server import APP_VERSION, GITHUB_REPO, RELEASE_ASSET, create_app


@pytest.fixture
def client():
    return TestClient(create_app())


def test_index_injects_app_version(client: TestClient):
    r = client.get("/")
    assert r.status_code == 200
    assert APP_VERSION in r.text
    assert f"app.css?v={APP_VERSION}" in r.text
    assert "no-store" in r.headers.get("cache-control", "")


def test_brain_status_when_offline(client: TestClient):
    with patch("persona.web.brain_routes.is_brain_available", return_value=False):
        r = client.get("/api/brain/status")
    assert r.status_code == 200
    assert r.json()["available"] is False


def test_brain_last_error(client: TestClient):
    with patch(
        "persona.web.brain_routes.get_last_brain_error",
        return_value={"capture": "test error", "rag": None},
    ):
        r = client.get("/api/brain/last-error")
    assert r.status_code == 200
    assert r.json()["capture"] == "test error"


def test_augment_message_with_rag_disabled(client: TestClient):
    from persona.web.brain_routes import augment_message_with_rag

    with patch("persona.web.brain_routes.is_brain_available", return_value=True):
        with patch(
            "persona.web.brain_routes.get_brain_config",
            return_value={"ragEnabled": False},
        ):
            assert augment_message_with_rag("hello") == "hello"


def test_brain_api_proxy_unavailable(client: TestClient):
    import httpx

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.request.side_effect = httpx.ConnectError(
            "down", request=httpx.Request("GET", "http://127.0.0.1:3002/api/brain/config")
        )
        r = client.get("/brain/api/brain/config")
    assert r.status_code == 502


def test_updates_endpoint_repo(client: TestClient):
    with patch("httpx.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"tag_name": "v0.9.0", "html_url": "https://example.com/release"},
        )
        r = client.get("/api/updates")
    assert r.status_code == 200
    data = r.json()
    assert data["current"] == APP_VERSION
    assert GITHUB_REPO in data.get("download_url", "") or GITHUB_REPO in data.get("url", "")
    assert RELEASE_ASSET in data.get("download_url", "")


def test_session_end_route(client: TestClient):
    with patch(
        "persona.web.brain_routes.flush_session_capture",
        return_value={"ok": True, "captured": 0},
    ) as flush:
        r = client.post("/api/brain/session-end")
    assert r.status_code == 200
    flush.assert_called_once()
