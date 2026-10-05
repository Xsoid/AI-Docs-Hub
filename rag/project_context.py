from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from .config import HUB_ROOT, ProjectConfig, get_project_config
from .docs_quality import documentation_readiness
from .project_lifecycle import quality_profile
from .security import is_excluded, safe_resolve, scan_text_for_secrets
from .skill_intelligence import get_skill_inventory
from .sources import build_source_plan


MAX_INSTRUCTION_FILES = 200
MAX_INSTRUCTION_DIRECTORIES = 10_000
MAX_SKILLS = 200
MAX_INSTRUCTION_BYTES = 250_000
INSTRUCTION_NAMES = {"AGENTS.MD": "agents", "CLAUDE.MD": "claude"}
PRUNED_DIRECTORIES = {
    ".git", "node_modules", "vendor", "cache", "storage", "tmp", "logs", ".venv", "venv"
}


def _config(project: str | ProjectConfig) -> ProjectConfig:
    return get_project_config(project) if isinstance(project, str) else project


def _hash_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _instruction_metadata(root: Path, path: Path) -> dict[str, Any]:
    relative = path.relative_to(root).as_posix()
    stat = path.stat()
    raw = path.read_bytes()
    kind = INSTRUCTION_NAMES[path.name.upper()]
    scope = path.parent.relative_to(root).as_posix() or "."
    return {
        "path": relative,
        "scope": scope,
        "kind": kind,
        "size_bytes": stat.st_size,
        "content_hash": _hash_bytes(raw),
    }


def discover_project_instructions(config: ProjectConfig) -> dict[str, Any]:
    """Discover bounded instruction metadata without returning file contents."""
    root = config.root.resolve()
    if not root.exists() or not root.is_dir():
        return {"items": [], "count": 0, "truncated": False, "limit": MAX_INSTRUCTION_FILES}

    source_exclude = build_source_plan(config).exclude
    candidates: list[Path] = []
    visited_directories = 0
    discovery_truncated = False
    for current, directories, filenames in os.walk(root, topdown=True, followlinks=False):
        visited_directories += 1
        if visited_directories > MAX_INSTRUCTION_DIRECTORIES:
            discovery_truncated = True
            break
        current_path = Path(current)
        directories[:] = sorted(
            directory for directory in directories
            if directory.lower() not in {item.lower() for item in PRUNED_DIRECTORIES}
            and not is_excluded((current_path / directory).relative_to(root).as_posix(), source_exclude)
        )
        for filename in sorted(filenames):
            if filename.upper() not in INSTRUCTION_NAMES:
                continue
            path = current_path / filename
            relative = path.relative_to(root).as_posix()
            if is_excluded(relative, source_exclude):
                continue
            try:
                resolved = path.resolve()
                resolved.relative_to(root)
                if not path.is_file():
                    continue
                candidates.append(path)
            except (OSError, ValueError):
                continue

    candidates.sort(key=lambda path: path.relative_to(root).as_posix().casefold())
    truncated = discovery_truncated or len(candidates) > MAX_INSTRUCTION_FILES
    items: list[dict[str, Any]] = []
    for path in candidates[:MAX_INSTRUCTION_FILES]:
        try:
            items.append(_instruction_metadata(root, path))
        except OSError:
            continue
    return {
        "items": items,
        "count": len(items),
        "truncated": truncated,
        "limit": MAX_INSTRUCTION_FILES,
    }


def _documentation_status(config: ProjectConfig) -> dict[str, Any]:
    readiness = documentation_readiness(config)
    base = {
        "index_exists": False,
        "indexed_at": None,
        "documents_count": 0,
        "chunks_count": 0,
        "readiness": {
            "status": readiness.get("status", "unknown"),
            "docs_dir": readiness.get("docs_dir", "docs"),
            "coverage": readiness.get("coverage", {}),
            "recommendation_count": len(readiness.get("recommendations", [])),
        },
    }
    index_path = config.index_path
    if not index_path.is_file():
        return {**base, "status": "missing", "recommendation": "index_project"}
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {**base, "status": "invalid", "recommendation": "index_project"}
    if index.get("project") != config.project or index.get("namespace") != config.namespace:
        return {**base, "status": "invalid", "recommendation": "index_project"}
    return {
        **base,
        "index_exists": True,
        "indexed_at": index.get("indexed_at"),
        "documents_count": int(index.get("documents_count", 0) or 0),
        "chunks_count": int(index.get("chunks_count", 0) or 0),
        "status": "ready",
        "recommendation": None,
    }


def _codebase_status() -> dict[str, Any]:
    binary = Path(os.environ.get("CODEBASE_MEMORY_BIN", HUB_ROOT / "storage/runtime/bin/codebase-memory-mcp"))
    return {"available": binary.is_file(), "status": "unknown"}


def _skill_catalog(config: ProjectConfig) -> tuple[list[dict[str, Any]], bool]:
    if not config.root.exists() or not config.root.is_dir():
        return [], False
    inventory = get_skill_inventory(config)
    skills = [
        {
            "name": skill.get("name", ""),
            "path": skill.get("path", ""),
            "status": "available",
            "description": str(skill.get("description", ""))[:500],
        }
        for skill in inventory.get("skills", [])
    ]
    skills.sort(key=lambda item: str(item["path"]).casefold())
    return skills[:MAX_SKILLS], len(skills) > MAX_SKILLS


def _has_git_patch(config: ProjectConfig) -> bool:
    root = config.root.resolve()
    if not (root / ".git").exists():
        return False
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=all"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and bool(result.stdout.strip())


def build_project_context(config: ProjectConfig) -> dict[str, Any]:
    from .context_freshness import current_context_identity

    instructions = discover_project_instructions(config)
    documentation = _documentation_status(config)
    codebase = _codebase_status()
    skills, skills_truncated = _skill_catalog(config)
    identity = current_context_identity(config)
    if config.root.exists() and config.root.is_dir():
        quality = quality_profile(config, persist=False)
        quality_status = {
            "profile_available": True,
            "checks_count": len(quality.get("verification", {}).get("checks", [])),
        }
    else:
        quality_status = {"profile_available": False, "checks_count": 0}
    next_tools: list[str] = []
    if documentation["status"] != "ready":
        next_tools.append("index_project")
    else:
        next_tools.append("search_docs")
    if codebase["available"]:
        next_tools.append("search_code")
    if _has_git_patch(config):
        next_tools.extend(["prepare_patch_review", "get_pre_publish_status"])
    return {
        "schema_version": 1,
        "project": config.project,
        "namespace": config.namespace,
        "context_fingerprint": identity["fingerprint"],
        "profile": {"title": config.title, "docs_backend": config.docs_backend},
        "documentation": documentation,
        "instructions": instructions["items"],
        "instruction_discovery": {
            "count": instructions["count"],
            "truncated": instructions["truncated"],
            "limit": instructions["limit"],
        },
        "skills": skills,
        "skill_discovery": {
            "count": len(skills),
            "truncated": skills_truncated,
            "limit": MAX_SKILLS,
        },
        "quality": quality_status,
        "codebase_memory": codebase,
        "capabilities": {
            "docs_search": True,
            "codebase_search": codebase["available"],
            "patch_review": True,
        },
        "recommended_next_tools": next_tools,
    }


def read_project_instruction(project: str | ProjectConfig, source_path: str) -> dict[str, Any]:
    config = _config(project)
    requested = source_path.strip().replace("\\", "/").lstrip("/")
    if not requested or requested.startswith("../") or "/../" in requested or requested == "..":
        raise PermissionError("Instruction path must be project-relative")
    manifest = discover_project_instructions(config)
    metadata = next((item for item in manifest["items"] if item["path"] == requested), None)
    if metadata is None:
        raise PermissionError("Path is not a discovered project instruction file")
    path = safe_resolve(config.root, requested)
    raw = path.read_bytes()
    truncated = len(raw) > MAX_INSTRUCTION_BYTES
    returned = raw[:MAX_INSTRUCTION_BYTES]
    text = returned.decode("utf-8", errors="replace")
    findings = scan_text_for_secrets(text)
    if findings:
        raise PermissionError(f"Refusing to return instruction with secret-like patterns: {requested}")
    return {
        "project": config.project,
        "namespace": config.namespace,
        "source_path": requested,
        "kind": metadata["kind"],
        "scope": metadata["scope"],
        "content_hash": _hash_bytes(returned),
        "truncated": truncated,
        "content": text,
    }
