"""Bundled local LLM — llama.cpp server + GGUF models shipped with Persona."""

from __future__ import annotations

import atexit
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from persona.config import Settings, get_settings

LLAMA_RELEASE = "b9861"
LLAMA_WIN_CPU_URL = (
    f"https://github.com/ggml-org/llama.cpp/releases/download/{LLAMA_RELEASE}/"
    f"llama-{LLAMA_RELEASE}-bin-win-cpu-x64.zip"
)

MODEL_TIERS: dict[str, dict[str, Any]] = {
    "fast": {
        "label": "Fast",
        "description": "Quick replies, lowest memory (~350 MB)",
        "filename": "fast.gguf",
        "bundled": True,
        "download_url": (
            "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/"
            "qwen2.5-0.5b-instruct-q4_k_m.gguf"
        ),
        "ram_gb_min": 4,
        "context": 2048,
        "supports_tools": False,
    },
    "balanced": {
        "label": "Balanced",
        "description": "Recommended default — good quality (~700 MB)",
        "filename": "balanced.gguf",
        "bundled": True,
        "default": True,
        "download_url": (
            "https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/"
            "Llama-3.2-1B-Instruct-Q4_K_M.gguf"
        ),
        "ram_gb_min": 6,
        "context": 4096,
        "supports_tools": False,
    },
    "quality": {
        "label": "Quality",
        "description": "Best answers + file tools — download once (~2 GB)",
        "filename": "quality.gguf",
        "bundled": False,
        "download_url": (
            "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/"
            "qwen2.5-3b-instruct-q4_k_m.gguf"
        ),
        "ram_gb_min": 8,
        "context": 8192,
        "supports_tools": True,
    },
}


def bundled_tier_supports_tools(tier: str) -> bool:
    spec = MODEL_TIERS.get(tier)
    return bool(spec and spec.get("supports_tools"))

_server_proc: subprocess.Popen[Any] | None = None
_server_lock = threading.Lock()
_download_state: dict[str, Any] = {
    "active": False,
    "tier": "",
    "progress": 0.0,
    "bytes_done": 0,
    "bytes_total": 0,
    "error": "",
}


@dataclass(frozen=True)
class BundledPaths:
    llama_dir: Path
    models_dir: Path
    user_models_dir: Path


def bundled_paths() -> BundledPaths:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS) / "llama"
        user_models = Path.home() / ".persona" / "models"
    else:
        base = Path(__file__).resolve().parents[2] / "vendor" / "llama"
        user_models = Path.home() / ".persona" / "models"
    return BundledPaths(
        llama_dir=base,
        models_dir=base / "models",
        user_models_dir=user_models,
    )


def llama_server_binary() -> Path | None:
    paths = bundled_paths()
    for name in ("llama-server.exe", "llama-server"):
        candidate = paths.llama_dir / name
        if candidate.is_file():
            return candidate
    return None


def bundled_binary_available() -> bool:
    return llama_server_binary() is not None


def model_path_for_tier(tier: str) -> Path | None:
    spec = MODEL_TIERS.get(tier)
    if not spec:
        return None
    paths = bundled_paths()
    filename = spec["filename"]
    if spec.get("bundled"):
        bundled = paths.models_dir / filename
        if bundled.is_file():
            return bundled
    user_file = paths.user_models_dir / filename
    if user_file.is_file():
        return user_file
    return None


def any_bundled_model_available() -> bool:
    return any(model_path_for_tier(t) is not None for t in MODEL_TIERS)


def bundled_ready(settings: Settings | None = None) -> bool:
    if not bundled_binary_available():
        return False
    settings = settings or Settings()
    tier = settings.bundled_model_tier
    if model_path_for_tier(tier):
        return True
    if tier != "balanced" and model_path_for_tier("balanced"):
        return True
    if model_path_for_tier("fast"):
        return True
    return any_bundled_model_available()


def resolve_active_tier(settings: Settings) -> str:
    tier = settings.bundled_model_tier or "balanced"
    if model_path_for_tier(tier):
        return tier
    for fallback in ("balanced", "fast", "quality"):
        if model_path_for_tier(fallback):
            return fallback
    return tier


def system_ram_gb() -> float:
    if sys.platform == "win32":
        try:
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                return stat.ullTotalPhys / (1024**3)
        except Exception:
            pass
    else:
        try:
            with open("/proc/meminfo", encoding="utf-8") as fh:
                for line in fh:
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        return kb / (1024**2)
        except Exception:
            pass
    return 16.0


def recommended_model_tier() -> str:
    ram = system_ram_gb()
    if ram >= 12:
        if model_path_for_tier("quality"):
            return "quality"
        return "balanced"
    if ram >= 8:
        return "balanced"
    return "fast"


def recommended_threads() -> int:
    cpus = os.cpu_count() or 4
    return max(2, min(cpus - 1, cpus // 2 + 2))


def resolve_gpu_layers(settings: Settings) -> int:
    if settings.bundled_gpu_layers >= 0:
        return settings.bundled_gpu_layers
    if sys.platform == "win32" and shutil.which("nvidia-smi"):
        return 35
    return 0


def resolve_threads(settings: Settings) -> int:
    if settings.bundled_threads > 0:
        return settings.bundled_threads
    return recommended_threads()


def bundled_server_url(settings: Settings) -> str:
    return f"http://127.0.0.1:{settings.bundled_port}"


def bundled_server_ready(settings: Settings, timeout: float = 2.0) -> bool:
    url = f"{bundled_server_url(settings)}/health"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if httpx.get(url, timeout=1.0).status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.2)
    return False


def _log_startup(message: str) -> None:
    if not getattr(sys, "frozen", False):
        return
    try:
        log_dir = Path.home() / ".persona"
        log_dir.mkdir(parents=True, exist_ok=True)
        with (log_dir / "startup.log").open("a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%H:%M:%S')} bundled: {message}\n")
    except Exception:
        pass


def start_bundled_server(settings: Settings, *, force: bool = False) -> bool:
    global _server_proc
    with _server_lock:
        if not force and _server_proc and _server_proc.poll() is None:
            if bundled_server_ready(settings, timeout=1.0):
                return True
            stop_bundled_server()

        binary = llama_server_binary()
        if not binary:
            _log_startup("llama-server binary not found")
            return False

        tier = resolve_active_tier(settings)
        model = model_path_for_tier(tier)
        if not model:
            _log_startup(f"no model file for tier={tier}")
            return False

        spec = MODEL_TIERS[tier]
        threads = resolve_threads(settings)
        ngl = resolve_gpu_layers(settings)
        port = settings.bundled_port

        cmd = [
            str(binary),
            "-m",
            str(model),
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "-c",
            str(spec.get("context", 4096)),
            "-t",
            str(threads),
            "-ngl",
            str(ngl),
        ]
        _log_startup(f"starting llama-server tier={tier} port={port} threads={threads} ngl={ngl}")

        creationflags = 0
        if sys.platform == "win32":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        try:
            _server_proc = subprocess.Popen(
                cmd,
                cwd=str(binary.parent),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
            )
        except Exception as exc:
            _log_startup(f"failed to start llama-server: {exc}")
            _server_proc = None
            return False

        if bundled_server_ready(settings, timeout=120.0):
            _log_startup("llama-server ready")
            return True

        _log_startup("llama-server did not become ready in time")
        stop_bundled_server()
        return False


def stop_bundled_server() -> None:
    global _server_proc
    with _server_lock:
        if _server_proc and _server_proc.poll() is None:
            _server_proc.terminate()
            try:
                _server_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                _server_proc.kill()
        _server_proc = None


def restart_bundled_server(settings: Settings) -> bool:
    stop_bundled_server()
    return start_bundled_server(settings, force=True)


atexit.register(stop_bundled_server)


def list_model_tiers(settings: Settings | None = None) -> list[dict[str, Any]]:
    settings = settings or Settings()
    active = resolve_active_tier(settings)
    ram = system_ram_gb()
    out: list[dict[str, Any]] = []
    for tier_id, spec in MODEL_TIERS.items():
        path = model_path_for_tier(tier_id)
        out.append(
            {
                "id": tier_id,
                "label": spec["label"],
                "description": spec["description"],
                "installed": path is not None,
                "active": tier_id == active,
                "bundled": bool(spec.get("bundled")),
                "ram_gb_min": spec.get("ram_gb_min", 4),
                "ram_ok": ram >= spec.get("ram_gb_min", 4),
                "size_mb": round(path.stat().st_size / (1024 * 1024)) if path else None,
                "supports_tools": spec.get("supports_tools", False),
            }
        )
    return out


def bundled_status(settings: Settings) -> dict[str, Any]:
    tier = resolve_active_tier(settings)
    ram = system_ram_gb()
    return {
        "available": bundled_ready(settings),
        "binary": bundled_binary_available(),
        "server_running": bundled_server_ready(settings, timeout=0.5),
        "active_tier": tier,
        "recommended_tier": recommended_model_tier(),
        "system_ram_gb": round(ram, 1),
        "ram_warning": ram < 8,
        "threads": resolve_threads(settings),
        "gpu_layers": resolve_gpu_layers(settings),
        "port": settings.bundled_port,
        "tools_supported": bundled_tier_supports_tools(tier),
        "models": list_model_tiers(settings),
        "download": dict(_download_state),
    }


def download_status() -> dict[str, Any]:
    return dict(_download_state)


def _download_model_file(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part")
    with httpx.stream("GET", url, follow_redirects=True, timeout=600.0) as response:
        response.raise_for_status()
        total = int(response.headers.get("content-length", "0") or 0)
        _download_state["bytes_total"] = total
        done = 0
        with tmp.open("wb") as fh:
            for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                fh.write(chunk)
                done += len(chunk)
                _download_state["bytes_done"] = done
                if total:
                    _download_state["progress"] = round(100.0 * done / total, 1)
    tmp.replace(dest)


def download_model(tier: str, settings: Settings) -> None:
    spec = MODEL_TIERS.get(tier)
    if not spec:
        raise ValueError(f"Unknown model tier: {tier}")
    if model_path_for_tier(tier):
        return
    url = spec.get("download_url")
    if not url:
        raise ValueError(f"Tier {tier} has no download URL")

    paths = bundled_paths()
    dest = paths.user_models_dir / spec["filename"]
    _download_state.update(
        {
            "active": True,
            "tier": tier,
            "progress": 0.0,
            "bytes_done": 0,
            "bytes_total": 0,
            "error": "",
        }
    )
    try:
        _download_model_file(url, dest)
        _download_state["progress"] = 100.0
    except Exception as exc:
        _download_state["error"] = str(exc)
        if dest.exists():
            dest.unlink(missing_ok=True)
        raise
    finally:
        _download_state["active"] = False


def download_model_async(tier: str, settings: Settings) -> bool:
    if _download_state.get("active"):
        return False

    def run() -> None:
        try:
            download_model(tier, settings)
        except Exception as exc:
            _download_state["error"] = str(exc)
            _download_state["active"] = False

    threading.Thread(target=run, daemon=True).start()
    return True


def save_bundled_preferences(updates: dict[str, Any]) -> dict[str, Any]:
    path = Path.home() / ".persona" / "preferences.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    current: dict[str, Any] = {}
    if path.exists():
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            current = {}
    current.update(updates)
    path.write_text(json.dumps(current, indent=2), encoding="utf-8")
    return current
