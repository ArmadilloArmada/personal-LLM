"""Tests for bundled local LLM support."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from persona.bundled import (
    MODEL_TIERS,
    bundled_paths,
    bundled_ready,
    list_model_tiers,
    model_path_for_tier,
    recommended_model_tier,
    recommended_threads,
    resolve_active_tier,
    resolve_gpu_layers,
    resolve_threads,
    system_ram_gb,
)
from persona.config import Settings
from persona.providers import resolve_provider_mode


def test_model_tiers_defined():
    assert set(MODEL_TIERS) == {"fast", "balanced", "quality"}
    assert MODEL_TIERS["balanced"].get("default")


def test_resolve_active_tier_prefers_installed(tmp_path, monkeypatch):
    paths = bundled_paths()
    monkeypatch.setattr(
        "persona.bundled.bundled_paths",
        lambda: type(paths)(
            llama_dir=tmp_path,
            models_dir=tmp_path / "models",
            user_models_dir=tmp_path / "user",
        ),
    )
    models = tmp_path / "models"
    models.mkdir(parents=True)
    (models / "fast.gguf").write_bytes(b"x" * 10)
    settings = Settings(bundled_model_tier="balanced")
    assert resolve_active_tier(settings) == "fast"


def test_bundled_ready_requires_binary_and_model(tmp_path, monkeypatch):
    paths = bundled_paths()
    monkeypatch.setattr(
        "persona.bundled.bundled_paths",
        lambda: type(paths)(
            llama_dir=tmp_path,
            models_dir=tmp_path / "models",
            user_models_dir=tmp_path / "user",
        ),
    )
    assert bundled_ready() is False
    (tmp_path / "llama-server.exe").write_text("bin", encoding="utf-8")
    models = tmp_path / "models"
    models.mkdir()
    (models / "balanced.gguf").write_bytes(b"x")
    assert bundled_ready() is True


def test_resolve_provider_bundled_when_frozen(monkeypatch):
    monkeypatch.setattr("sys.frozen", True, raising=False)
    monkeypatch.setenv("PERSONA_PROVIDER", "")
    monkeypatch.setattr("persona.providers.bundled_ready", lambda s=None: True)
    assert resolve_provider_mode(Settings()) == "bundled"


def test_resolve_provider_auto_prefers_bundled(monkeypatch):
    monkeypatch.delattr("sys", "frozen", raising=False)
    monkeypatch.setattr("persona.providers.bundled_ready", lambda s=None: True)
    monkeypatch.setattr("persona.providers.ollama_ready", lambda s: False)
    assert resolve_provider_mode(Settings(provider="auto")) == "bundled"


def test_recommended_threads_reasonable():
    assert recommended_threads() >= 2


def test_system_ram_gb_positive():
    assert system_ram_gb() > 0


def test_list_model_tiers_structure(monkeypatch):
    monkeypatch.setattr("persona.bundled.model_path_for_tier", lambda t: None)
    tiers = list_model_tiers(Settings())
    assert len(tiers) == 3
    assert all("label" in t and "installed" in t for t in tiers)


def test_resolve_gpu_layers_respects_settings():
    settings = Settings(bundled_gpu_layers=0)
    assert resolve_gpu_layers(settings) == 0


def test_recommended_model_tier_with_ram(monkeypatch):
    monkeypatch.setattr("persona.bundled.system_ram_gb", lambda: 16.0)
    monkeypatch.setattr("persona.bundled.model_path_for_tier", lambda t: Path("x") if t == "quality" else None)
    assert recommended_model_tier() == "quality"
