from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import (
    HUB_ROOT,
    ProjectConfig,
    expand_path_variables,
    get_project_config,
    is_hardcoded_absolute_root,
)
from .project_lifecycle import (
    _git_root,
    _head,
    _run_git,
    _status_paths,
    patch_fingerprint,
)
from .project_context import discover_project_instructions
from .skill_intelligence import get_skill_inventory


SCHEMA_VERSION = 1
SNAPSHOT_DIR = HUB_ROOT / "storage" / "context-snapshots"
SNAPSHOT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
COMPONENT_NAMES = ("git", "config", "instructions", "docs_index", "skills", "codebase_index")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _config(project: str | ProjectConfig) -> ProjectConfig:
    return get_project_config(project) if isinstance(project, str) else project


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _component(*, status: str, payload: Any = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "status": status,
        "fingerprint": canonical_hash(payload) if payload is not None else None,
        "metadata": metadata or {},
    }


def _git_identity(config: ProjectConfig) -> dict[str, Any]:
    root = config.root.resolve()
    if not root.exists() or not (root / ".git").exists():
        return _component(status="unavailable", metadata={"repository_present": False})
    try:
        git_root = _git_root(root)
        tracked, untracked = _status_paths(git_root)
        patch = patch_fingerprint(config, scope="working")
        branch = _run_git(git_root, ["symbolic-ref", "--short", "-q", "HEAD"], check=False).stdout.strip() or None
        payload = {
            "repository_id": patch.get("repository_id"),
            "head": _head(git_root),
            "branch": branch,
            "changed_files": patch.get("changed_files", []),
            "untracked_files": patch.get("untracked_files", []),
            "patch_fingerprint": patch.get("fingerprint"),
        }
        return _component(
            status="available",
            payload=payload,
            metadata={
                "repository_present": True,
                "head": payload["head"],
                "branch": branch,
                "dirty": bool(tracked or untracked),
                "changed_files_count": len(payload["changed_files"]),
                "untracked_files_count": len(payload["untracked_files"]),
            },
        )
    except Exception as exc:  # noqa: BLE001
        return _component(status="unavailable", metadata={"repository_present": True, "reason": type(exc).__name__})


def _portable_root_identity(config: ProjectConfig) -> str:
    source = str(config.root_source).strip().replace("\\", "/")
    if not source:
        return ""
    if is_hardcoded_absolute_root(source):
        return "<absolute-root>"
    expanded, unresolved = expand_path_variables(source)
    if unresolved:
        return source
    return expanded.replace("\\", "/")


def _config_identity(config: ProjectConfig) -> dict[str, Any]:
    sources = [
        {"path": str(source.get("path", "")), "type": str(source.get("type", ""))}
        for source in config.sources
    ]
    payload = {
        "schema_version": config.schema_version,
        "project": config.project,
        "namespace": config.namespace,
        "title": config.title,
        "root": _portable_root_identity(config),
        "docs_backend": config.docs_backend,
        "mkdocs_config": config.mkdocs_config.replace("\\", "/"),
        "sources": sorted(sources, key=canonical_json),
        "include": sorted(str(value) for value in config.include),
        "exclude": sorted(str(value) for value in config.exclude),
        "agent_rules": list(config.agent_rules),
    }
    return _component(status="available", payload=payload, metadata={"schema_version": config.schema_version})


def _instructions_identity(config: ProjectConfig) -> dict[str, Any]:
    discovered = discover_project_instructions(config)
    items = [
        {"path": item["path"], "scope": item["scope"], "kind": item["kind"], "content_hash": item["content_hash"]}
        for item in discovered["items"]
    ]
    payload = {"items": items, "truncated": discovered["truncated"]}
    status = "degraded" if discovered["truncated"] else "available"
    return _component(
        status=status,
        payload=payload,
        metadata={"count": discovered["count"], "truncated": discovered["truncated"]},
    )


def _docs_index_identity(config: ProjectConfig) -> dict[str, Any]:
    path = config.index_path
    if not path.is_file():
        return _component(status="unavailable", metadata={"index_exists": False})
    try:
        index = json.loads(path.read_text(encoding="utf-8"))
        if index.get("project") != config.project or index.get("namespace") != config.namespace:
            return _component(status="unavailable", metadata={"index_exists": True, "reason": "identity_mismatch"})
        documents = [
            {"source_path": str(document.get("source_path", "")), "content_hash": str(document.get("content_hash", ""))}
            for document in index.get("documents", [])
            if isinstance(document, dict)
        ]
        payload = {
            "backend": index.get("backend"),
            "schema_version": index.get("schema_version"),
            "source_plan": index.get("source_plan", {}),
            "documents": sorted(documents, key=canonical_json),
        }
        return _component(
            status="available",
            payload=payload,
            metadata={
                "index_exists": True,
                "indexed_at": index.get("indexed_at"),
                "documents_count": int(index.get("documents_count", 0) or 0),
                "chunks_count": int(index.get("chunks_count", 0) or 0),
            },
        )
    except (OSError, ValueError, TypeError):
        return _component(status="unavailable", metadata={"index_exists": True, "reason": "invalid_index"})


def _skills_identity(config: ProjectConfig) -> dict[str, Any]:
    if not config.root.exists() or not config.root.is_dir():
        return _component(status="unavailable", metadata={"count": 0})
    try:
        inventory = get_skill_inventory(config)
        skills = [
            {
                "path": str(skill.get("path", "")),
                "name": str(skill.get("name", "")),
                "content_hash": str(skill.get("content_hash", "")),
                "status": "available",
            }
            for skill in inventory.get("skills", [])
            if isinstance(skill, dict)
        ]
        skills.sort(key=canonical_json)
        blocked = [str(item.get("source_path", "")) for item in inventory.get("blocked_sources", []) if isinstance(item, dict)]
        status = "degraded" if blocked else "available"
        return _component(status=status, payload={"skills": skills, "blocked": sorted(blocked)}, metadata={"count": len(skills), "blocked_count": len(blocked)})
    except Exception as exc:  # noqa: BLE001
        return _component(status="unavailable", metadata={"reason": type(exc).__name__})


def _codebase_identity() -> dict[str, Any]:
    binary = Path(os.environ.get("CODEBASE_MEMORY_BIN", HUB_ROOT / "storage/runtime/bin/codebase-memory-mcp"))
    if not binary.is_file():
        return _component(status="unavailable", metadata={"available": False})
    return _component(status="unknown", metadata={"available": True})


def _overall_fingerprint(components: dict[str, dict[str, Any]]) -> str:
    return canonical_hash({
        name: {"status": component.get("status"), "fingerprint": component.get("fingerprint")}
        for name, component in sorted(components.items())
    })


def current_context_identity(project: str | ProjectConfig) -> dict[str, Any]:
    config = _config(project)
    components = {
        "git": _git_identity(config),
        "config": _config_identity(config),
        "instructions": _instructions_identity(config),
        "docs_index": _docs_index_identity(config),
        "skills": _skills_identity(config),
        "codebase_index": _codebase_identity(),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "project": config.project,
        "namespace": config.namespace,
        "fingerprint": _overall_fingerprint(components),
        "components": components,
    }


def context_fingerprint(project: str | ProjectConfig) -> str:
    return current_context_identity(project)["fingerprint"]


def _snapshot_project_dir(config: ProjectConfig) -> Path:
    root = SNAPSHOT_DIR.resolve()
    project_dir = (SNAPSHOT_DIR / config.project).resolve()
    if not project_dir.is_relative_to(root):
        raise ValueError("Context snapshot path escapes local Hub storage")
    return project_dir


def _snapshot_path(config: ProjectConfig, snapshot_id: str) -> Path:
    if not SNAPSHOT_ID_RE.fullmatch(snapshot_id):
        raise ValueError("Invalid context snapshot id")
    path = (_snapshot_project_dir(config) / f"{snapshot_id}.json").resolve()
    if not path.parent.is_relative_to(SNAPSHOT_DIR.resolve()):
        raise ValueError("Context snapshot path escapes local Hub storage")
    return path


def capture_project_context(project: str | ProjectConfig) -> dict[str, Any]:
    config = _config(project)
    identity = current_context_identity(config)
    snapshot_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:12]}"
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "snapshot_id": snapshot_id,
        "captured_at": _utc_now(),
        "project": config.project,
        "namespace": config.namespace,
        "fingerprint": identity["fingerprint"],
        "components": identity["components"],
    }
    path = _snapshot_path(config, snapshot_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    snapshot_path = str(path.relative_to(HUB_ROOT)) if path.is_relative_to(HUB_ROOT) else None
    return {**snapshot, "snapshot_path": snapshot_path}


def _compare_components(snapshot: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    changed: list[str] = []
    unchanged: list[str] = []
    unknown: list[str] = []
    snapshot_components = snapshot.get("components") if isinstance(snapshot.get("components"), dict) else {}
    current_components = current.get("components") if isinstance(current.get("components"), dict) else {}
    for name in COMPONENT_NAMES:
        old = snapshot_components.get(name) if isinstance(snapshot_components.get(name), dict) else {}
        new = current_components.get(name) if isinstance(current_components.get(name), dict) else {}
        old_status = str(old.get("status", "unknown"))
        new_status = str(new.get("status", "unknown"))
        old_fingerprint = old.get("fingerprint")
        new_fingerprint = new.get("fingerprint")
        if old_status not in {"available"} or new_status not in {"available"} or old_fingerprint is None or new_fingerprint is None:
            unknown.append(name)
        elif old_fingerprint != new_fingerprint:
            changed.append(name)
        else:
            unchanged.append(name)
    if changed:
        state = "stale"
    elif unknown:
        state = "degraded"
    else:
        state = "fresh"
    return {
        "state": state,
        "changed_components": changed,
        "unchanged_components": unchanged,
        "unknown_components": unknown,
        "current_fingerprint": current.get("fingerprint"),
        "snapshot_fingerprint": snapshot.get("fingerprint"),
    }


def check_project_context(project: str | ProjectConfig, snapshot_id: str) -> dict[str, Any]:
    config = _config(project)
    path = _snapshot_path(config, snapshot_id)
    if not path.is_file():
        return {
            "project": config.project,
            "namespace": config.namespace,
            "snapshot_id": snapshot_id,
            "state": "missing",
            "changed_components": [],
            "unchanged_components": [],
            "unknown_components": [],
        }
    try:
        snapshot = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {
            "project": config.project,
            "namespace": config.namespace,
            "snapshot_id": snapshot_id,
            "state": "degraded",
            "changed_components": [],
            "unchanged_components": [],
            "unknown_components": COMPONENT_NAMES,
            "reason": "invalid_snapshot",
        }
    if snapshot.get("project") != config.project or snapshot.get("namespace") != config.namespace:
        raise ValueError("Context snapshot belongs to another project")
    current = current_context_identity(config)
    return {
        "project": config.project,
        "namespace": config.namespace,
        "snapshot_id": snapshot_id,
        "captured_at": snapshot.get("captured_at"),
        **_compare_components(snapshot, current),
    }
