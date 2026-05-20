from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from .config import (
    CONFIGS_DIR,
    HUB_ROOT,
    INDEX_DIR,
    is_unbound_example_config,
    load_project_configs,
    validate_project_config,
)
from .docs_quality import documentation_readiness


def _command_output(command: str, *args: str) -> tuple[str | None, str | None]:
    path = shutil.which(command)
    if not path:
        return None, None
    try:
        result = subprocess.run(
            [path, *args],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=5,
            check=False,
        )
    except OSError as exc:
        return path, f"failed to run: {exc}"
    except subprocess.TimeoutExpired:
        return path, "version check timed out"
    return path, result.stdout.strip()


def _node_major(version: str | None) -> int | None:
    if not version:
        return None
    match = re.search(r"v?(\d+)", version)
    return int(match.group(1)) if match else None


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

    python_ok = sys.version_info >= (3, 11)
    add(
        "python_runtime",
        "ok" if python_ok else "error",
        f"Python {sys.version.split()[0]} {'is supported' if python_ok else 'is too old; install Python 3.11+'}",
        executable=sys.executable,
    )

    node_path, node_version = _command_output("node", "--version")
    node_major = _node_major(node_version)
    if not node_path:
        add("node_runtime", "error", "Node.js is missing; install Node.js 22 LTS")
    elif node_major != 22:
        add(
            "node_runtime",
            "warning",
            f"Node.js {node_version} found; Node.js 22 LTS is the supported runtime",
            executable=node_path,
        )
    else:
        add("node_runtime", "ok", f"Node.js {node_version} found", executable=node_path)

    npm_path, npm_version = _command_output("npm", "--version")
    if not npm_path:
        add("npm_runtime", "error", "npm is missing; install Node.js 22 LTS with npm")
    else:
        add("npm_runtime", "ok", f"npm {npm_version} found", executable=npm_path)

    try:
        INDEX_DIR.mkdir(parents=True, exist_ok=True)
        probe = INDEX_DIR / f".healthcheck-{os.getpid()}"
        try:
            probe.write_text("ok", encoding="utf-8")
        finally:
            probe.unlink(missing_ok=True)
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
            recommendations = [issue for issue in issues if issue["level"] == "recommendation"]
            if errors:
                add("project_config", "error", f"{name} has config errors", issues=issues)
            elif warnings:
                if is_unbound_example_config(config):
                    add("project_config", "ok", f"{name} is an unbound sample config", issues=issues)
                else:
                    add("project_config", "warning", f"{name} has config warnings", issues=issues)
            else:
                message = f"{name} config is valid"
                if recommendations:
                    message = f"{name} config is valid with documentation recommendations"
                add("project_config", "ok", message, issues=issues)

            if not is_unbound_example_config(config):
                readiness = documentation_readiness(config)
                if readiness.get("status") == "needs_work":
                    add(
                        "documentation_readiness",
                        "ok",
                        f"{name} documentation has recommended gaps",
                        project=name,
                        severity="recommendation",
                        coverage=readiness.get("coverage", {}),
                        recommendations=readiness.get("recommendations", []),
                    )
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
