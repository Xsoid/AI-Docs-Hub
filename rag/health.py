from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .config import CONFIGS_DIR, HUB_ROOT, INDEX_DIR, load_project_configs, validate_project_config


def run_healthcheck() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def add(name: str, status: str, message: str, **extra: Any) -> None:
        item: dict[str, Any] = {"name": name, "status": status, "message": message}
        item.update(extra)
        checks.append(item)

    required_paths = [
        ("configs", CONFIGS_DIR),
        ("storage", HUB_ROOT / "storage"),
        ("index_dir", INDEX_DIR),
        ("docs_site", HUB_ROOT / "docs-site"),
        ("mcp_server", HUB_ROOT / "mcp" / "server.py"),
    ]
    for name, path in required_paths:
        add(name, "ok" if path.exists() else "error", f"{path} {'exists' if path.exists() else 'is missing'}")

    try:
        INDEX_DIR.mkdir(parents=True, exist_ok=True)
        probe = INDEX_DIR / ".healthcheck"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        add("storage_writable", "ok", "storage/index is writable")
    except OSError as exc:
        add("storage_writable", "error", f"storage/index is not writable: {exc}")

    try:
        configs = load_project_configs()
        if not configs:
            add("project_configs", "warning", "no project configs found")
        for name, config in configs.items():
            issues = validate_project_config(config)
            errors = [issue for issue in issues if issue["level"] == "error"]
            warnings = [issue for issue in issues if issue["level"] == "warning"]
            if errors:
                add("project_config", "error", f"{name} has config errors", issues=issues)
            elif warnings:
                add("project_config", "warning", f"{name} has config warnings", issues=issues)
            else:
                add("project_config", "ok", f"{name} config is valid")
    except Exception as exc:  # noqa: BLE001
        add("project_configs", "error", f"failed to load configs: {exc}")

    index_count = len(list(INDEX_DIR.glob("*.json"))) if INDEX_DIR.exists() else 0
    add("rag_backend", "ok", "lite RAG backend selected", backend="lite-json-bm25", index_count=index_count)

    package_json = HUB_ROOT / "docs-site" / "package.json"
    add("docs_package", "ok" if package_json.exists() else "error", f"{package_json} check")

    status = "ok"
    if any(check["status"] == "error" for check in checks):
        status = "error"
    elif any(check["status"] == "warning" for check in checks):
        status = "degraded"

    return {
        "status": status,
        "hub_root": str(HUB_ROOT),
        "cwd": os.getcwd(),
        "checks": checks,
    }

