from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .config import HUB_ROOT, ProjectConfig, get_project_config, is_placeholder_path
from .mcp_clients import (
    CODEBASE_SERVER_SCRIPT,
    DOCS_SERVER_SCRIPT,
    HUB_SERVER,
    atomic_write_json,
    codebase_cache_dir,
    codebase_memory_available,
    codebase_server_name,
    configured_projects,
    docs_server_name,
    is_hub_entry,
    read_json_object,
    stdio_entry,
)


class KimiConfigError(RuntimeError):
    """Raised when the Kimi Code user config cannot be read or written safely."""


def kimi_config_path() -> Path:
    configured = os.environ.get("KIMI_CODE_HOME", "").strip()
    home = Path(configured).expanduser() if configured else Path.home() / ".kimi-code"
    return home / "mcp.json"


def desired_servers(project: str | None, *, codebase_memory: bool | None = None) -> dict[str, dict[str, Any]]:
    """Return the Hub-managed MCP entries for the user-level Kimi Code config."""
    if project is None:
        return {HUB_SERVER: stdio_entry(DOCS_SERVER_SCRIPT)}
    servers = {docs_server_name(project): stdio_entry(DOCS_SERVER_SCRIPT, "--project", project)}
    if codebase_memory_available(project) if codebase_memory is None else codebase_memory:
        servers[codebase_server_name(project)] = stdio_entry(
            CODEBASE_SERVER_SCRIPT, "--project", project, env={"CBM_CACHE_DIR": str(codebase_cache_dir())}
        )
    return servers


def _managed_names(project: str | None) -> set[str]:
    if project is None:
        return {HUB_SERVER}
    return {docs_server_name(project), codebase_server_name(project)}


def _target(project: str | None) -> str | None:
    if project is None:
        return None
    config: ProjectConfig = get_project_config(project)
    if is_placeholder_path(config.root_source) or not config.root.is_dir():
        raise KimiConfigError(f"project root for {project} is not an existing directory")
    if config.root.resolve() == HUB_ROOT.resolve():
        raise KimiConfigError("the Hub checkout is configured with --hub, not as a connected project")
    return config.project


def _status_for(data: dict[str, Any], project: str | None, desired: dict[str, dict[str, Any]]) -> dict[str, Any]:
    current = data.get("mcpServers") or {}
    servers = {}
    for name, entry in desired.items():
        present = current.get(name)
        servers[name] = "configured" if present == entry else "missing" if present is None else "foreign" if not is_hub_entry(present) else "outdated"
    stale = sorted(name for name in _managed_names(project) if name in current and name not in desired and is_hub_entry(current[name]))
    return {
        "project": project or "ai-docs-hub",
        "scope": "hub" if project is None else "project",
        "servers": servers,
        "stale_hub_servers": stale,
        "configured": all(state == "configured" for state in servers.values()) and not stale,
    }


def _apply_servers(current: dict[str, Any], desired: dict[str, dict[str, Any]], managed: set[str]) -> list[str]:
    changes: list[str] = []
    for name in sorted(current):
        if name in managed and name not in desired and is_hub_entry(current[name]):
            changes.append(f"remove {name}")
            del current[name]
    for name, entry in desired.items():
        if current.get(name) == entry or (name in current and not is_hub_entry(current[name])):
            continue
        changes.append(f"set {name}")
        current[name] = entry
    return changes


def _read_config(path: Path) -> dict[str, Any]:
    return read_json_object(path, KimiConfigError)


def _write_config(path: Path, data: dict[str, Any]) -> None:
    atomic_write_json(path, data, temp_prefix=".mcp.json.")


def kimi_mcp_status(project: str | None) -> dict[str, Any]:
    project = _target(project)
    return {**_status_for(_read_config(kimi_config_path()), project, desired_servers(project)), "kimi_config": str(kimi_config_path())}


def configure_kimi_mcp(project: str | None, *, write: bool = False, remove: bool = False) -> dict[str, Any]:
    """Install or remove Hub MCP entries in the user-level Kimi Code config.

    Only entries that point to this Hub checkout are replaced or removed, and only
    within the server names managed for this target. A same-named server owned by
    someone else is reported as ``foreign`` and left untouched; entries of other
    projects and the unscoped Hub server are never removed.
    """
    project = _target(project)
    path = kimi_config_path()
    desired = {} if remove else desired_servers(project)
    # Re-read immediately before the atomic replace: the user may edit this file between runs.
    data = _read_config(path)
    before = _status_for(data, project, desired_servers(project))
    current = data.setdefault("mcpServers", {})
    changes = _apply_servers(current, desired, _managed_names(project))
    if write and changes:
        _write_config(path, data)
    # A dry-run reports the unchanged on-disk state; ``changes`` lists what --write would do.
    after = _status_for(_read_config(path), project, desired_servers(project))
    return {
        **after,
        "action": "remove" if remove else "configure",
        "write": write,
        "changes": changes,
        "configured_before": before["configured"],
        "restart_required": bool(write and changes),
        "kimi_config": str(path),
    }


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Register AI Docs Hub MCP servers for Kimi Code (user-level mcp.json)")
    parser.add_argument("command", choices=["status", "configure", "remove"])
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--project")
    target.add_argument("--all", action="store_true", help="every connected project with an existing root")
    target.add_argument("--hub", action="store_true", help="the unscoped Hub server for this checkout")
    parser.add_argument("--write", action="store_true", help="apply the change; the default is a dry-run")
    args = parser.parse_args(argv)
    targets: list[str | None] = [None] if args.hub else configured_projects() if args.all else [args.project]
    results = []
    failed = False
    for project in targets:
        try:
            if args.command == "status":
                results.append(kimi_mcp_status(project))
            else:
                results.append(configure_kimi_mcp(project, write=args.write, remove=args.command == "remove"))
        except (KimiConfigError, KeyError, OSError) as exc:
            failed = True
            results.append({"project": project or "ai-docs-hub", "status": "error", "error": str(exc)})
    print(json.dumps(results if len(results) != 1 else results[0], ensure_ascii=False, indent=2))
    return 1 if failed else 0
