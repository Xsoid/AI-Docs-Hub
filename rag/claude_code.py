from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .config import HUB_ROOT, ProjectConfig, get_project_config, is_placeholder_path
from .mcp_clients import (  # noqa: F401  (re-exported for existing imports)
    CODEBASE_SERVER_SCRIPT,
    DEFAULT_CODEBASE_BINARY,
    DEFAULT_CODEBASE_CACHE,
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


class ClaudeConfigError(RuntimeError):
    """Raised when the Claude Code user config cannot be read or written safely."""


def claude_config_path() -> Path:
    configured = os.environ.get("CLAUDE_CONFIG_DIR", "").strip()
    return (Path(configured).expanduser() if configured else Path.home()) / ".claude.json"


def _codebase_cache_dir() -> Path:
    return codebase_cache_dir()


def _stdio(script: Path, *args: str, env: dict[str, str] | None = None) -> dict[str, Any]:
    return stdio_entry(script, *args, env=env, typed=True)


def desired_servers(project: str | None, *, codebase_memory: bool | None = None) -> dict[str, dict[str, Any]]:
    """Return the Hub-managed MCP entries for one Claude Code project directory."""
    if project is None:
        return {HUB_SERVER: _stdio(DOCS_SERVER_SCRIPT)}
    servers = {docs_server_name(project): _stdio(DOCS_SERVER_SCRIPT, "--project", project)}
    if codebase_memory_available(project) if codebase_memory is None else codebase_memory:
        servers[codebase_server_name(project)] = _stdio(CODEBASE_SERVER_SCRIPT, "--project", project, env={"CBM_CACHE_DIR": str(_codebase_cache_dir())})
    return servers


def _is_hub_entry(entry: Any) -> bool:
    return is_hub_entry(entry)


def _read_config(path: Path) -> dict[str, Any]:
    return read_json_object(path, ClaudeConfigError)


def _write_config(path: Path, data: dict[str, Any]) -> None:
    atomic_write_json(path, data, temp_prefix=".claude.json.")


def _target(project: str | None) -> tuple[str | None, Path]:
    if project is None:
        return None, HUB_ROOT.resolve()
    config: ProjectConfig = get_project_config(project)
    if is_placeholder_path(config.root_source) or not config.root.is_dir():
        raise ClaudeConfigError(f"project root for {project} is not an existing directory")
    if config.root.resolve() == HUB_ROOT.resolve():
        raise ClaudeConfigError("the Hub checkout is configured with --hub, not as a connected project")
    return config.project, config.root.resolve()


def _status_for(data: dict[str, Any], project: str | None, root: Path, desired: dict[str, dict[str, Any]]) -> dict[str, Any]:
    current = ((data.get("projects") or {}).get(str(root)) or {}).get("mcpServers") or {}
    servers = {}
    for name, entry in desired.items():
        present = current.get(name)
        servers[name] = "configured" if present == entry else "missing" if present is None else "foreign" if not _is_hub_entry(present) else "outdated"
    stale = sorted(name for name, entry in current.items() if name not in desired and _is_hub_entry(entry))
    return {
        "project": project or "ai-docs-hub",
        "scope": "hub" if project is None else "project",
        "claude_project_dir": str(root),
        "servers": servers,
        "stale_hub_servers": stale,
        "configured": all(state == "configured" for state in servers.values()) and not stale,
    }


def _apply_servers(current: dict[str, Any], desired: dict[str, dict[str, Any]]) -> list[str]:
    changes: list[str] = []
    for name, entry in list(current.items()):
        if name not in desired and _is_hub_entry(entry):
            changes.append(f"remove {name}")
            del current[name]
    for name, entry in desired.items():
        if current.get(name) == entry or (name in current and not _is_hub_entry(current[name])):
            continue
        changes.append(f"set {name}")
        current[name] = entry
    return changes


def claude_mcp_status(project: str | None) -> dict[str, Any]:
    project, root = _target(project)
    return _status_for(_read_config(claude_config_path()), project, root, desired_servers(project))


def configure_claude_mcp(project: str | None, *, write: bool = False, remove: bool = False) -> dict[str, Any]:
    """Install or remove Hub MCP entries in the local scope of one Claude Code project directory.

    Only entries that point to this Hub checkout are replaced or removed. A same-named
    server owned by someone else is reported as ``foreign`` and left untouched.
    """
    project, root = _target(project)
    path = claude_config_path()
    desired = {} if remove else desired_servers(project)
    # Re-read immediately before the atomic replace: the Claude Code app also writes this file.
    data = _read_config(path)
    before = _status_for(data, project, root, desired_servers(project))
    current = data.setdefault("projects", {}).setdefault(str(root), {}).setdefault("mcpServers", {})
    changes = _apply_servers(current, desired)
    if write and changes:
        _write_config(path, data)
    # A dry-run reports the unchanged on-disk state; ``changes`` lists what --write would do.
    after = _status_for(_read_config(path), project, root, desired_servers(project))
    return {
        **after,
        "action": "remove" if remove else "configure",
        "write": write,
        "changes": changes,
        "configured_before": before["configured"],
        "restart_required": bool(write and changes),
        "claude_config": str(path),
    }


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Register AI Docs Hub MCP servers for Claude Code (local scope)")
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
                results.append(claude_mcp_status(project))
            else:
                results.append(configure_claude_mcp(project, write=args.write, remove=args.command == "remove"))
        except (ClaudeConfigError, KeyError, OSError) as exc:
            failed = True
            results.append({"project": project or "ai-docs-hub", "status": "error", "error": str(exc)})
    print(json.dumps(results if len(results) != 1 else results[0], ensure_ascii=False, indent=2))
    return 1 if failed else 0
