"""Configuration loaded from environment variables."""

import json
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _load_preferences() -> dict:
    path = Path.home() / ".persona" / "preferences.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PERSONA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    provider: str = "auto"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    max_tool_rounds: int = 15
    workspace: Path = Field(default_factory=lambda: Path.cwd())
    active_workspace: str = "default"
    web_host: str = "127.0.0.1"
    web_port: int = 8765
    bundled_port: int = 11435
    bundled_model_tier: str = "balanced"
    bundled_threads: int = 0
    bundled_gpu_layers: int = -1

    @property
    def data_dir(self) -> Path:
        path = Path.home() / ".persona"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def memory_file(self) -> Path:
        return self.data_dir / "memory.json"

    @property
    def sessions_dir(self) -> Path:
        path = self.data_dir / "sessions"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def custom_personas_dir(self) -> Path:
        path = self.data_dir / "personas"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def workspace_personas_dir(self) -> Path:
        path = self.workspace / "personas"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def projects_dir(self) -> Path:
        path = self.data_dir / "projects"
        path.mkdir(parents=True, exist_ok=True)
        return path


def get_settings() -> Settings:
    return Settings(**_load_preferences())
