from __future__ import annotations

import json
import os
import re
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

from .config import HUB_ROOT


SCHEMA_VERSION = 1
DEFAULT_RETENTION_DAYS = 30
DEFAULT_WINDOW_HOURS = 24
PROJECT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
DATE_FILE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.jsonl$")

HUB_SERVER = "local-ai-docs-hub"
CODEBASE_SERVER = "codebase-memory-proxy"

READ_TOOLS = {
    "list_projects", "get_project_profile", "get_project_context", "read_project_instruction",
    "capture_project_context", "check_project_context", "search_docs", "read_doc",
    "search_decisions", "search_modules", "healthcheck", "lint_project", "read_operation_log",
    "analyze_skill_candidates", "get_skill_inventory", "get_skill_proposal", "validate_skill_architecture",
    "get_quality_profile", "prepare_patch_review", "get_pre_publish_status", "get_mcp_usage_summary",
}
MUTATION_TOOLS = {
    "index_project", "scaffold_project_docs", "create_skill_proposal", "create_skill_evolution_proposal",
    "apply_skill_proposal", "verify_patch", "record_code_review", "record_security_review", "onboard_project",
}
CODEBASE_READ_TOOLS = {
    "detect_changes", "get_architecture", "get_code_snippet", "get_graph_schema", "index_status",
    "query_graph", "search_code", "search_graph", "trace_call_path", "trace_path",
}
CONFIRM_TOOLS = {"index_project", "scaffold_project_docs", "apply_skill_proposal", "onboard_project"}


def audit_directory() -> Path:
    return Path(os.environ.get("MCP_AUDIT_DIR", HUB_ROOT / "storage" / "mcp-audit")).resolve()


def retention_days() -> int:
    try:
        return max(1, min(int(os.environ.get("MCP_AUDIT_RETENTION_DAYS", DEFAULT_RETENTION_DAYS)), 3650))
    except (TypeError, ValueError):
        return DEFAULT_RETENTION_DAYS


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def timestamp(value: datetime | None = None) -> str:
    return (value or utc_now()).isoformat().replace("+00:00", "Z")


def safe_project(value: Any) -> str | None:
    candidate = str(value or "")
    return candidate if PROJECT_RE.fullmatch(candidate) else None


def tool_class(server: str, tool: str) -> str:
    if server == CODEBASE_SERVER:
        return "read" if tool in CODEBASE_READ_TOOLS else "other"
    if tool in READ_TOOLS:
        return "read"
    if tool in MUTATION_TOOLS:
        return "write"
    return "other"


def _safe_metadata(server: str, tool: str, arguments: dict[str, Any] | None) -> dict[str, Any]:
    args = arguments or {}
    metadata: dict[str, Any] = {}
    if tool in CONFIRM_TOOLS:
        metadata["confirm"] = bool(args.get("confirm", False))
    for key in ("reindex", "detailed", "fill_empty"):
        if tool in {"index_project", "lint_project", "scaffold_project_docs"} and key in args:
            metadata[key] = bool(args[key])
    for key in ("scope", "kind"):
        value = args.get(key)
        if isinstance(value, str) and value in {"working", "staged", "range", "branch", "code", "security"}:
            metadata[key] = value
    return metadata


def _error_category(error: BaseException | None) -> str | None:
    if error is None:
        return None
    return type(error).__name__


def _result_size(result: Any) -> int:
    try:
        return len(json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    except (TypeError, ValueError):
        return 0


def _cleanup(directory: Path, now: datetime) -> None:
    cutoff = now.date() - timedelta(days=retention_days() - 1)
    try:
        for path in directory.iterdir():
            if not path.is_file() or not DATE_FILE_RE.fullmatch(path.name):
                continue
            try:
                if datetime.strptime(path.stem, "%Y-%m-%d").date() < cutoff:
                    path.unlink()
            except (OSError, ValueError):
                continue
    except OSError:
        return


def write_event(event: dict[str, Any]) -> None:
    """Best-effort append of one sanitized event; audit must never break MCP."""
    directory = audit_directory()
    now = utc_now()
    path = directory / f"{now.date().isoformat()}.jsonl"
    try:
        directory.mkdir(parents=True, exist_ok=True)
        line = json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line)
        _cleanup(directory, now)
    except (OSError, TypeError, ValueError):
        return


class AuditCall:
    def __init__(self, *, server: str, project: Any, tool: str, arguments: dict[str, Any] | None = None, client: str | None = None):
        self.server = server
        self.project = safe_project(project)
        self.tool = tool if PROJECT_RE.fullmatch(tool) else "unknown"
        self.arguments = arguments or {}
        client_value = client.replace("/", "-") if isinstance(client, str) else ""
        client_value = re.sub(r"[^A-Za-z0-9._-]+", "-", client_value).strip("-._")
        self.client = client_value[:100] if client_value else None
        self.started = time.monotonic()
        self.status = "ok"
        self.is_error = False
        self.error = None
        self.result_size_bytes = 0

    def finish(self, *, status: str = "ok", is_error: bool = False, result: Any = None, error: BaseException | None = None) -> None:
        self.status = status if status in {"ok", "error"} else "error"
        self.is_error = bool(is_error)
        self.error = _error_category(error)
        self.result_size_bytes = _result_size(result)

    def event(self) -> dict[str, Any]:
        event: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "timestamp": timestamp(),
            "server": self.server,
            "transport": "stdio",
            "tool": self.tool,
            "tool_class": tool_class(self.server, self.tool),
            "duration_ms": max(0, round((time.monotonic() - self.started) * 1000)),
            "status": self.status,
            "is_error": self.is_error,
            "result_size_bytes": self.result_size_bytes,
        }
        if self.project:
            event["project"] = self.project
        metadata = _safe_metadata(self.server, self.tool, self.arguments)
        if metadata:
            event["metadata"] = metadata
        if self.error:
            event["error_category"] = self.error
        if self.client:
            event["client"] = self.client
        return event

    def __enter__(self) -> "AuditCall":
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: Any) -> bool:
        if exc is not None:
            self.finish(status="error", is_error=True, error=exc)
        try:
            write_event(self.event())
        except Exception:  # noqa: BLE001
            # Observability is strictly best-effort and must never alter MCP behavior.
            pass
        return False


@contextmanager
def audit_tool_call(*, server: str, project: Any, tool: str, arguments: dict[str, Any] | None = None, client: str | None = None) -> Iterator[AuditCall]:
    with AuditCall(server=server, project=project, tool=tool, arguments=arguments, client=client) as call:
        yield call


def _iter_events(*, now: datetime, window_hours: int) -> Iterator[dict[str, Any]]:
    directory = audit_directory()
    cutoff = now - timedelta(hours=window_hours)
    try:
        paths = sorted(directory.glob("*.jsonl"))
    except OSError:
        return
    for path in paths:
        if not DATE_FILE_RE.fullmatch(path.name):
            continue
        try:
            with path.open(encoding="utf-8") as handle:
                for line in handle:
                    try:
                        event = json.loads(line)
                        if not isinstance(event, dict):
                            continue
                        event_time = datetime.fromisoformat(str(event.get("timestamp", "")).replace("Z", "+00:00"))
                        if event_time >= cutoff:
                            yield event
                    except (json.JSONDecodeError, TypeError, ValueError, OverflowError):
                        continue
        except OSError:
            continue


def usage_summary(*, project: str | None = None, window_hours: int = DEFAULT_WINDOW_HOURS) -> dict[str, Any]:
    hours = max(1, min(int(window_hours), 24 * 7))
    selected_project = safe_project(project) if project else None
    if project is not None and selected_project is None:
        raise ValueError("invalid project filter")
    calls = 0
    errors = 0
    tools: dict[str, dict[str, int]] = {}
    servers: dict[str, int] = {}
    for event in _iter_events(now=utc_now(), window_hours=hours):
        if event.get("tool") == "get_mcp_usage_summary":
            continue
        if selected_project is not None and event.get("project") != selected_project:
            continue
        tool = str(event.get("tool", "unknown"))
        server = str(event.get("server", "unknown"))
        calls += 1
        is_error = bool(event.get("is_error")) or event.get("status") == "error"
        errors += int(is_error)
        counts = tools.setdefault(tool, {"calls": 0, "errors": 0})
        counts["calls"] += 1
        counts["errors"] += int(is_error)
        servers[server] = servers.get(server, 0) + 1
    return {
        "project": selected_project,
        "window": f"{hours}h",
        "calls": calls,
        "errors": errors,
        "tools": {name: tools[name] for name in sorted(tools)},
        "servers": {name: servers[name] for name in sorted(servers)},
    }
