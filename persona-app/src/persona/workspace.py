"""Team workspace management — shared boards, docs, and crew per company."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class TeamWorkspace:
    id: str
    name: str
    company: str = ""
    members: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "company": self.company,
            "members": self.members,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class WorkspaceManager:
    def __init__(self, data_dir: Path):
        self.root = data_dir / "workspaces"
        self.root.mkdir(parents=True, exist_ok=True)
        self._active_file = data_dir / "active_workspace.txt"
        self._ensure_default()

    def _ensure_default(self) -> None:
        if not (self.root / "default.json").exists():
            now = datetime.now(timezone.utc).isoformat()
            default = TeamWorkspace(
                id="default",
                name="Personal",
                company="",
                members=["you"],
                created_at=now,
                updated_at=now,
            )
            self._save(default)
        if not self._active_file.exists():
            self._active_file.write_text("default", encoding="utf-8")

    def _path(self, workspace_id: str) -> Path:
        return self.root / f"{workspace_id}.json"

    def _save(self, workspace: TeamWorkspace) -> None:
        self._path(workspace.id).write_text(
            json.dumps(workspace.to_dict(), indent=2), encoding="utf-8"
        )

    def workspace_dir(self, workspace_id: str) -> Path:
        path = self.root / workspace_id
        path.mkdir(parents=True, exist_ok=True)
        (path / "docs").mkdir(exist_ok=True)
        return path

    def get_active_id(self) -> str:
        return self._active_file.read_text(encoding="utf-8").strip() or "default"

    def set_active(self, workspace_id: str) -> TeamWorkspace:
        ws = self.get(workspace_id)
        if not ws:
            raise KeyError(workspace_id)
        self._active_file.write_text(workspace_id, encoding="utf-8")
        return ws

    def get(self, workspace_id: str) -> TeamWorkspace | None:
        path = self._path(workspace_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return TeamWorkspace(**data)

    def list_all(self) -> list[TeamWorkspace]:
        workspaces = []
        for path in sorted(self.root.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                workspaces.append(TeamWorkspace(**data))
            except Exception:
                continue
        return workspaces

    def create(self, name: str, company: str = "", members: list[str] | None = None) -> TeamWorkspace:
        now = datetime.now(timezone.utc).isoformat()
        ws = TeamWorkspace(
            id=str(uuid.uuid4())[:8],
            name=name,
            company=company,
            members=members or ["you"],
            created_at=now,
            updated_at=now,
        )
        self._save(ws)
        self.workspace_dir(ws.id)
        return ws

    def add_member(self, workspace_id: str, member: str) -> TeamWorkspace:
        ws = self.get(workspace_id)
        if not ws:
            raise KeyError(workspace_id)
        if member not in ws.members:
            ws.members.append(member)
        ws.updated_at = datetime.now(timezone.utc).isoformat()
        self._save(ws)
        return ws
