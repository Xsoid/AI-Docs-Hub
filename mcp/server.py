#!/usr/bin/env python3.11
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rag.health import run_healthcheck  # noqa: E402
from rag.lint import lint_project  # noqa: E402
from rag.lite import (  # noqa: E402
    build_index,
    get_project_config,
    list_projects,
    project_profile,
    read_project_doc,
    search_decisions,
    search_index,
    search_modules,
)
from rag.logging import read_operation_log  # noqa: E402


Json = dict[str, Any]


class McpServer:
    def __init__(self, active_project: str | None = None):
        self.active_project = active_project
        self.tools: dict[str, Callable[[Json], Json]] = {
            "list_projects": self.tool_list_projects,
            "get_project_profile": self.tool_get_project_profile,
            "search_docs": self.tool_search_docs,
            "read_doc": self.tool_read_doc,
            "search_decisions": self.tool_search_decisions,
            "search_modules": self.tool_search_modules,
            "index_project": self.tool_index_project,
            "healthcheck": self.tool_healthcheck,
            "lint_project": self.tool_lint_project,
            "read_operation_log": self.tool_read_operation_log,
        }

    def resolve_project(self, args: Json) -> str:
        requested = args.get("project")
        if self.active_project:
            if requested and requested != self.active_project:
                raise PermissionError(
                    f"This MCP server is scoped to project '{self.active_project}', not '{requested}'."
                )
            return self.active_project
        if not requested:
            raise ValueError("project is required")
        return str(requested)

    def tool_list_projects(self, args: Json) -> Json:
        projects = list_projects()
        return {"active_project": self.active_project, "projects": projects}

    def tool_get_project_profile(self, args: Json) -> Json:
        return project_profile(self.resolve_project(args))

    def tool_search_docs(self, args: Json) -> Json:
        project = self.resolve_project(args)
        query = str(args.get("query", "")).strip()
        if not query:
            raise ValueError("query is required")
        limit = int(args.get("limit", 8))
        return search_index(project, query, limit=limit)

    def tool_read_doc(self, args: Json) -> Json:
        project = self.resolve_project(args)
        source_path = str(args.get("source_path", "")).strip()
        if not source_path:
            raise ValueError("source_path is required")
        return read_project_doc(project, source_path)

    def tool_search_decisions(self, args: Json) -> Json:
        project = self.resolve_project(args)
        query = str(args.get("query", "")).strip()
        if not query:
            raise ValueError("query is required")
        limit = int(args.get("limit", 8))
        return search_decisions(project, query, limit=limit)

    def tool_search_modules(self, args: Json) -> Json:
        project = self.resolve_project(args)
        module_name = str(args.get("module_name", "")).strip()
        if not module_name:
            raise ValueError("module_name is required")
        limit = int(args.get("limit", 8))
        return search_modules(project, module_name, limit=limit)

    def tool_index_project(self, args: Json) -> Json:
        project = self.resolve_project(args)
        confirm = bool(args.get("confirm", False))
        if not confirm:
            return {
                "requires_confirmation": True,
                "risk": "Indexing reads configured project files and writes a local index under storage/index.",
                "safe_default": "No indexing was started because confirm=true was not provided.",
                "command": f"make index PROJECT={project}",
                "mcp_call": {
                    "tool": "index_project",
                    "arguments": {"project": project, "confirm": True},
                },
            }
        config = get_project_config(project)
        if not config.root.exists():
            raise ValueError(
                f"Project root does not exist: {config.root}. "
                "Set configs/projects/*.yaml root to an absolute external project path."
            )
        index = build_index(config, reindex=bool(args.get("reindex", False)))
        return {
            "project": project,
            "namespace": index["namespace"],
            "documents_count": index["documents_count"],
            "chunks_count": index["chunks_count"],
            "index_path": str(config.index_path),
        }

    def tool_healthcheck(self, args: Json) -> Json:
        return run_healthcheck()

    def tool_lint_project(self, args: Json) -> Json:
        project = self.resolve_project(args)
        detailed = bool(args.get("detailed", False))
        return lint_project(project, detailed=detailed)

    def tool_read_operation_log(self, args: Json) -> Json:
        project = self.resolve_project(args)
        limit = int(args.get("limit", 20))
        entries = read_operation_log(project, limit=limit)
        return {
            "project": project,
            "log_entries": entries,
            "total_entries": len(entries),
        }

    def tool_specs(self) -> list[Json]:
        project_property = {
            "type": "string",
            "description": "Project name from configs/projects. Optional when server was started with --project.",
        }
        return [
            {
                "name": "list_projects",
                "description": "List available project configs and namespaces.",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "get_project_profile",
                "description": "Return project title, sources, include/exclude patterns, agent rules, and index status.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"project": project_property},
                    "required": [] if self.active_project else ["project"],
                },
            },
            {
                "name": "search_docs",
                "description": "Search project docs inside one namespace and return snippets with sources and confidence.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project": project_property,
                        "query": {"type": "string"},
                        "limit": {"type": "integer", "default": 8, "minimum": 1, "maximum": 50},
                    },
                    "required": ["query"] if self.active_project else ["project", "query"],
                },
            },
            {
                "name": "read_doc",
                "description": "Read an allowed project document by source_path.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project": project_property,
                        "source_path": {"type": "string"},
                    },
                    "required": ["source_path"] if self.active_project else ["project", "source_path"],
                },
            },
            {
                "name": "search_decisions",
                "description": "Search ADR and architecture decision documents for one project.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project": project_property,
                        "query": {"type": "string"},
                        "limit": {"type": "integer", "default": 8, "minimum": 1, "maximum": 50},
                    },
                    "required": ["query"] if self.active_project else ["project", "query"],
                },
            },
            {
                "name": "search_modules",
                "description": "Search docs and README files for a specific module name.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project": project_property,
                        "module_name": {"type": "string"},
                        "limit": {"type": "integer", "default": 8, "minimum": 1, "maximum": 50},
                    },
                    "required": ["module_name"] if self.active_project else ["project", "module_name"],
                },
            },
            {
                "name": "index_project",
                "description": "Index one project. Requires confirm=true to actually start indexing.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project": project_property,
                        "confirm": {"type": "boolean", "default": False},
                        "reindex": {"type": "boolean", "default": False},
                    },
                    "required": [] if self.active_project else ["project"],
                },
            },
            {
                "name": "healthcheck",
                "description": "Check configs, storage, lite RAG backend, and docs-site files.",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "lint_project",
                "description": "Run structural lint checks on project: broken wiki-links, orphan pages, empty documents, duplicate headings.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project": project_property,
                        "detailed": {"type": "boolean", "default": False},
                    },
                    "required": [] if self.active_project else ["project"],
                },
            },
            {
                "name": "read_operation_log",
                "description": "Read indexing operation logs for a project (JSONL format).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project": project_property,
                        "limit": {"type": "integer", "default": 20, "minimum": 1, "maximum": 100},
                    },
                    "required": [] if self.active_project else ["project"],
                },
            },
        ]

    def handle_request(self, message: Json) -> Json | None:
        method = message.get("method")
        request_id = message.get("id")
        if method == "initialize":
            params = message.get("params") or {}
            protocol_version = params.get("protocolVersion") or "2025-06-18"
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": protocol_version,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "local-ai-docs-hub", "version": "0.1.0"},
                },
            }
        if method == "notifications/initialized":
            return None
        if method == "ping":
            return {"jsonrpc": "2.0", "id": request_id, "result": {}}
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": self.tool_specs()}}
        if method == "tools/call":
            params = message.get("params") or {}
            name = params.get("name")
            args = params.get("arguments") or {}
            if name not in self.tools:
                return self.error(request_id, -32602, f"Unknown tool: {name}")
            try:
                result = self.tools[str(name)](dict(args))
                text = json.dumps(result, ensure_ascii=False)
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": text}],
                        "structuredContent": result,
                        "isError": False,
                    },
                }
            except Exception as exc:  # noqa: BLE001
                payload = {"error": str(exc), "tool": name}
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}],
                        "structuredContent": payload,
                        "isError": True,
                    },
                }
        return self.error(request_id, -32601, f"Method not found: {method}")

    @staticmethod
    def error(request_id: Any, code: int, message: str) -> Json:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}

    def run(self) -> None:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
                response = self.handle_request(message)
            except Exception as exc:  # noqa: BLE001
                response = self.error(None, -32700, f"Parse or server error: {exc}")
            if response is not None:
                sys.stdout.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")
                sys.stdout.flush()


def main() -> int:
    parser = argparse.ArgumentParser(description="Local AI Docs Hub MCP stdio server")
    parser.add_argument("--project", help="Optional project scope")
    args = parser.parse_args()
    McpServer(active_project=args.project).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
