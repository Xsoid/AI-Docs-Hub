from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from .config import HUB_ROOT, is_placeholder_path, load_project_configs


HUB_SERVER = "local_ai_docs_hub"
DOCS_SERVER_SCRIPT = HUB_ROOT / "mcp" / "server.py"
CODEBASE_SERVER_SCRIPT = HUB_ROOT / "mcp" / "codebase_memory_proxy.py"
DEFAULT_CODEBASE_BINARY = HUB_ROOT / "storage" / "runtime" / "bin" / "codebase-memory-mcp"
DEFAULT_CODEBASE_CACHE = HUB_ROOT / "storage" / "codebase-memory"


def _slug(project: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in project).strip("_")


def docs_server_name(project: str) -> str:
    return f"{_slug(project)}_docs"


def codebase_server_name(project: str) -> str:
    return f"codebase_{_slug(project)}"


def codebase_cache_dir() -> Path:
    return Path(os.environ.get("CBM_CACHE_DIR", DEFAULT_CODEBASE_CACHE)).expanduser()


def codebase_memory_available(project: str) -> bool:
    """Codebase Memory is registered only when the binary exists and the project graph is built."""
    configured = os.environ.get("CODEBASE_MEMORY_BIN", "").strip()
    binary = Path(configured).expanduser() if configured else DEFAULT_CODEBASE_BINARY
    return binary.is_file() and (codebase_cache_dir() / f"{project}.db").is_file()


def stdio_entry(script: Path, *args: str, env: dict[str, str] | None = None, typed: bool = False) -> dict[str, Any]:
    entry: dict[str, Any] = {"command": sys.executable, "args": [str(script), *args], "env": env or {}}
    return {"type": "stdio", **entry} if typed else entry


def is_hub_entry(entry: Any) -> bool:
    if not isinstance(entry, dict) or not isinstance(entry.get("args"), list) or not entry["args"]:
        return False
    return str(entry["args"][0]) in {str(DOCS_SERVER_SCRIPT), str(CODEBASE_SERVER_SCRIPT)}


def read_json_object(path: Path, error_class: type[RuntimeError]) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise error_class(f"{path} is not valid JSON; refusing to modify it") from exc
    if not isinstance(data, dict):
        raise error_class(f"{path} must contain a JSON object")
    return data


def atomic_write_json(path: Path, data: dict[str, Any], *, temp_prefix: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
    handle, temp_name = tempfile.mkstemp(prefix=temp_prefix, dir=str(path.parent))
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp_name, mode)
        os.replace(temp_name, path)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise


def configured_projects() -> list[str]:
    return sorted(name for name, config in load_project_configs().items() if not is_placeholder_path(config.root_source) and config.root.is_dir())
