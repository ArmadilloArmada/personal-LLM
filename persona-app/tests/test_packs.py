"""Tests for persona pack export/import."""

from pathlib import Path

import pytest

from persona.config import Settings
from persona.crew import Crew
from persona.custom import export_persona_pack_yaml, import_persona_pack_yaml, persona_from_dict
from persona.personas import PERSONAS, get_persona


@pytest.fixture
def crew(tmp_path: Path) -> Crew:
    settings = Settings(provider="demo", workspace=tmp_path)
    return Crew(settings)


def test_export_import_roundtrip(tmp_path: Path):
    settings = Settings(provider="demo", workspace=tmp_path)
    from persona.custom import reload_persona_registry, save_custom_persona

    persona = persona_from_dict(
        {
            "id": "ledger",
            "name": "Ledger",
            "role": "Accountant",
            "tagline": "Numbers with clarity.",
            "emoji": "📊",
            "instructions": "You are Ledger, our finance specialist.",
        }
    )
    save_custom_persona(persona, settings.custom_personas_dir)
    reload_persona_registry(settings)
    yaml_content = export_persona_pack_yaml(
        ["ledger"],
        name="Finance Pack",
        description="Test pack",
    )
    assert "Ledger" in yaml_content
    imported = import_persona_pack_yaml(yaml_content, settings.custom_personas_dir)
    assert len(imported) == 1
    assert imported[0].name == "Ledger"


def test_export_rejects_builtin_only():
    with pytest.raises(ValueError, match="No exportable"):
        export_persona_pack_yaml(["byte", "captain"])


def test_crew_import_pack(crew: Crew, tmp_path: Path):
    pack = """
name: Test Pack
personas:
  - id: scout
    name: Scout
    role: Scout
    tagline: Finds the path.
    instructions: You are Scout, a trail guide.
"""
    result = crew.import_persona_pack(pack)
    assert len(result) == 1
    assert result[0]["name"] == "Scout"
    assert get_persona("scout").name == "Scout"
