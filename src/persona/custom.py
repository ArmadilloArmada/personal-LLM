"""Load and save custom company/user personas from YAML files."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from persona.personas import BASE_GUIDELINES, PERSONAS, Persona, persona_to_dict

VALID_SHAPES = {"round", "square", "star", "blob", "shield", "hexagon", "diamond"}
VALID_TOOLS = {
    "read_file",
    "write_file",
    "list_directory",
    "run_shell",
    "web_fetch",
    "remember",
    "forget",
    "search_docs",
}
BUILTIN_IDS = frozenset({"byte", "sunny", "nova", "sketch", "captain"})


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "persona"


def persona_from_dict(data: dict[str, Any], *, is_custom: bool = True) -> Persona:
    persona_id = _slugify(str(data.get("id") or data.get("name", "custom")))
    name = str(data.get("name", persona_id.title()))
    role = str(data.get("role", "Specialist"))
    tagline = str(data.get("tagline", f"Your {role.lower()} on the crew."))
    color = str(data.get("color", "#6366F1"))
    accent = str(data.get("accent", "#312E81"))
    emoji = str(data.get("emoji", "🤖"))
    shape = str(data.get("shape", "hexagon"))
    if shape not in VALID_SHAPES:
        shape = "hexagon"
    personality = str(data.get("personality", "Helpful and on-brand."))
    specialties = [str(s) for s in data.get("specialties", [role.lower()])]
    tools = [str(t) for t in data.get("tools", ["remember", "forget"]) if t in VALID_TOOLS]
    company = str(data.get("company", ""))
    instructions = str(
        data.get("system_prompt")
        or data.get("instructions")
        or f"You are {name}, the {role} persona. {personality}"
    )
    system_prompt = f"{instructions.strip()}\n{BASE_GUIDELINES}"

    return Persona(
        id=persona_id,
        name=name,
        role=role,
        tagline=tagline,
        color=color,
        accent=accent,
        emoji=emoji,
        shape=shape,
        personality=personality,
        specialties=specialties,
        tools=tools,
        system_prompt=system_prompt,
        is_custom=is_custom,
        company=company,
    )


def load_custom_personas(*directories: Path) -> dict[str, Persona]:
    loaded: dict[str, Persona] = {}
    for directory in directories:
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*")):
            if path.suffix.lower() not in (".yaml", ".yml", ".json"):
                continue
            try:
                raw = path.read_text(encoding="utf-8")
                data = json.loads(raw) if path.suffix.lower() == ".json" else yaml.safe_load(raw)
                if not data:
                    continue
                entries = data if isinstance(data, list) else data.get("personas", [data])
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    persona = persona_from_dict(entry)
                    if persona.id in BUILTIN_IDS:
                        continue
                    loaded[persona.id] = persona
            except Exception:
                continue
    return loaded


def save_custom_persona(persona: Persona, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{persona.id}.yaml"
    payload = {
        "id": persona.id,
        "name": persona.name,
        "role": persona.role,
        "tagline": persona.tagline,
        "color": persona.color,
        "accent": persona.accent,
        "emoji": persona.emoji,
        "shape": persona.shape,
        "personality": persona.personality,
        "specialties": persona.specialties,
        "tools": persona.tools,
        "company": persona.company,
        "instructions": persona.system_prompt.replace(BASE_GUIDELINES, "").strip(),
    }
    path.write_text(yaml.dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def delete_custom_persona(persona_id: str, directory: Path) -> bool:
    for ext in (".yaml", ".yml", ".json"):
        path = directory / f"{persona_id}{ext}"
        if path.exists():
            path.unlink()
            return True
    return False


def persona_to_export_entry(persona: Persona) -> dict[str, Any]:
    return {
        "id": persona.id,
        "name": persona.name,
        "role": persona.role,
        "tagline": persona.tagline,
        "color": persona.color,
        "accent": persona.accent,
        "emoji": persona.emoji,
        "shape": persona.shape,
        "personality": persona.personality,
        "specialties": persona.specialties,
        "tools": persona.tools,
        "company": persona.company,
        "instructions": persona.system_prompt.replace(BASE_GUIDELINES, "").strip(),
    }


def export_persona_pack_yaml(
    persona_ids: list[str],
    *,
    name: str = "Persona Pack",
    description: str = "",
) -> str:
    """Serialize custom personas into a shareable YAML pack."""
    entries: list[dict[str, Any]] = []
    for pid in persona_ids:
        persona = PERSONAS.get(pid)
        if not persona or pid in BUILTIN_IDS:
            continue
        entries.append(persona_to_export_entry(persona))
    if not entries:
        raise ValueError("No exportable agents found. Built-in agents cannot be exported.")
    payload: dict[str, Any] = {
        "name": name,
        "description": description,
        "version": 1,
        "personas": entries,
    }
    return yaml.dump(payload, sort_keys=False, allow_unicode=True)


def import_persona_pack_yaml(content: str, directory: Path) -> list[Persona]:
    """Import personas from a YAML pack into the user's persona directory."""
    data = yaml.safe_load(content)
    if not data:
        raise ValueError("Pack file is empty or invalid.")
    entries = data if isinstance(data, list) else data.get("personas", [data])
    imported: list[Persona] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        persona = persona_from_dict(entry)
        if persona.id in BUILTIN_IDS:
            continue
        save_custom_persona(persona, directory)
        imported.append(persona)
    if not imported:
        raise ValueError("No valid agents found in pack.")
    return imported


def pack_filename(name: str) -> str:
    slug = _slugify(name) or "persona-pack"
    return f"{slug}.yaml"


def merge_persona_registry(custom: dict[str, Persona]) -> None:
    for pid in list(PERSONAS.keys()):
        if PERSONAS[pid].is_custom:
            del PERSONAS[pid]
    PERSONAS.update(custom)


def _shipped_persona_dirs() -> list[Path]:
    """Built-in persona packs shipped with the app."""
    dirs: list[Path] = []
    here = Path(__file__).resolve()
    candidates = [
        here.parents[1] / "personas",
        here.parents[1] / "personas" / "packs",
        here.parents[2] / "personas",
        here.parents[2] / "personas" / "packs",
    ]
    import sys

    if getattr(sys, "frozen", False):
        meipass = Path(getattr(sys, "_MEIPASS", ""))
        candidates.extend([meipass / "personas", meipass / "personas" / "packs"])
    for path in candidates:
        if path.exists() and path not in dirs:
            dirs.append(path)
    return dirs


def reload_persona_registry(settings) -> list[Persona]:
    custom = load_custom_personas(
        settings.custom_personas_dir,
        settings.workspace_personas_dir,
        *_shipped_persona_dirs(),
    )
    merge_persona_registry(custom)
    return list(PERSONAS.values())
