"""Persona avatar storage and URLs."""

from __future__ import annotations

from pathlib import Path

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
MAX_AVATAR_BYTES = 2 * 1024 * 1024


class AvatarStore:
    def __init__(self, data_dir: Path):
        self.dir = data_dir / "avatars"
        self.dir.mkdir(parents=True, exist_ok=True)

    def path_for(self, persona_id: str) -> Path | None:
        for ext in ALLOWED_EXTENSIONS:
            path = self.dir / f"{persona_id}{ext}"
            if path.exists():
                return path
        return None

    def save(self, persona_id: str, filename: str, data: bytes) -> Path:
        if len(data) > MAX_AVATAR_BYTES:
            raise ValueError("Avatar file too large (max 2MB)")
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported image type: {ext}")
        for old in self.dir.glob(f"{persona_id}.*"):
            old.unlink(missing_ok=True)
        path = self.dir / f"{persona_id}{ext}"
        path.write_bytes(data)
        return path

    def delete(self, persona_id: str) -> bool:
        deleted = False
        for path in self.dir.glob(f"{persona_id}.*"):
            path.unlink()
            deleted = True
        return deleted

    def url_for(self, persona_id: str) -> str | None:
        path = self.path_for(persona_id)
        if not path:
            return None
        return f"/api/avatars/{persona_id}{path.suffix}"
