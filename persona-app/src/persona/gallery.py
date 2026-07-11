"""Curated persona pack gallery — one-click import."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from persona.custom import import_persona_pack_yaml


def _gallery_dirs() -> list[Path]:
    here = Path(__file__).resolve()
    candidates = [
        here.parents[1] / "personas" / "gallery",
        here.parents[2] / "personas" / "gallery",
    ]
    import sys

    if getattr(sys, "frozen", False):
        meipass = Path(getattr(sys, "_MEIPASS", ""))
        candidates.append(meipass / "personas" / "gallery")
    return [p for p in candidates if p.is_dir()]


def list_gallery_packs() -> list[dict[str, Any]]:
    packs: dict[str, dict[str, Any]] = {}
    for directory in _gallery_dirs():
        for path in sorted(directory.glob("*.yaml")) + sorted(directory.glob("*.yml")):
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(data, dict):
                continue
            pack_id = path.stem
            personas = data.get("personas", [])
            if isinstance(personas, dict):
                personas = [personas]
            packs[pack_id] = {
                "id": pack_id,
                "name": data.get("name", pack_id.replace("-", " ").title()),
                "description": data.get("description", ""),
                "emoji": data.get("emoji", "📦"),
                "agent_count": len(personas) if isinstance(personas, list) else 0,
                "agents": [
                    {"id": p.get("id"), "name": p.get("name"), "role": p.get("role"), "emoji": p.get("emoji", "🤖")}
                    for p in personas
                    if isinstance(p, dict)
                ],
            }
    return list(packs.values())


def load_gallery_pack_yaml(pack_id: str) -> str:
    safe_id = pack_id.replace("..", "").strip("/")
    for directory in _gallery_dirs():
        for ext in (".yaml", ".yml"):
            path = directory / f"{safe_id}{ext}"
            if path.is_file():
                return path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Gallery pack not found: {pack_id}")


def import_gallery_pack(pack_id: str, directory: Path) -> list[str]:
    content = load_gallery_pack_yaml(pack_id)
    imported = import_persona_pack_yaml(content, directory)
    return [p.id for p in imported]
