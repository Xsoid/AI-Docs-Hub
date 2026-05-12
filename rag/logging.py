from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import HUB_ROOT, INDEX_DIR


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_project_log_path(project: str) -> Path:
    """Get the log file path for a project."""
    return INDEX_DIR / f"{project}_log.jsonl"


def log_operation(project: str, operation: str, data: dict[str, Any]) -> None:
    """Append a single operation log entry (JSONL format).
    
    Args:
        project: Project name
        operation: Operation name (e.g., 'index_started', 'index_complete', 'secret_scan_blocked')
        data: Additional operation data
    """
    log_path = get_project_log_path(project)
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    
    entry = {
        "timestamp": utc_now(),
        "project": project,
        "operation": operation,
        **data,
    }
    
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_operation_log(project: str, limit: int | None = None) -> list[dict[str, Any]]:
    """Read operation log for a project. Returns most recent entries first."""
    log_path = get_project_log_path(project)
    if not log_path.exists():
        return []
    
    entries: list[dict[str, Any]] = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    
    # Most recent first
    entries.reverse()
    return entries[:limit] if limit else entries


def log_index_started(project: str, reindex: bool = False, reason: str = "") -> None:
    """Log when indexing starts."""
    log_operation(project, "index_started", {
        "reindex": reindex,
        "reason": reason,
    })


def log_index_complete(project: str, documents_count: int, chunks_count: int, duration_seconds: float) -> None:
    """Log when indexing completes successfully."""
    log_operation(project, "index_complete", {
        "documents_count": documents_count,
        "chunks_count": chunks_count,
        "duration_seconds": round(duration_seconds, 2),
    })


def log_index_error(project: str, error_type: str, error_message: str) -> None:
    """Log when indexing fails."""
    log_operation(project, "index_error", {
        "error_type": error_type,
        "error_message": str(error_message),
    })


def log_secret_scan_blocked(project: str, blocked_count: int, blocked_files: list[str]) -> None:
    """Log when secret scan blocks indexing."""
    log_operation(project, "secret_scan_blocked", {
        "blocked_count": blocked_count,
        "blocked_files": blocked_files[:10],  # Keep first 10
    })


def log_lint_check(project: str, broken_links_count: int, orphan_pages_count: int, issues: list[dict[str, Any]]) -> None:
    """Log a lint check."""
    log_operation(project, "lint_check", {
        "broken_links_count": broken_links_count,
        "orphan_pages_count": orphan_pages_count,
        "total_issues": len(issues),
    })
