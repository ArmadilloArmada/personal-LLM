"""Tests for persona gallery packs."""

from pathlib import Path

import pytest

from persona.config import Settings
from persona.crew import Crew
from persona.gallery import import_gallery_pack, list_gallery_packs, load_gallery_pack_yaml


def test_list_gallery_packs():
    packs = list_gallery_packs()
    assert len(packs) >= 5
    ids = {p["id"] for p in packs}
    assert "indie-hacker" in ids


def test_load_gallery_pack_yaml():
    content = load_gallery_pack_yaml("dm-table")
    assert "Dungeon Master" in content or "DM" in content


def test_import_gallery_pack(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    settings = Settings(provider="demo", workspace=tmp_path)
    crew = Crew(settings)
    personas = crew.import_gallery_pack("fitness-crew")
    names = {p["name"] for p in personas}
    assert "Coach" in names
