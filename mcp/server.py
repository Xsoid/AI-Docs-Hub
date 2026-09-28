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
from rag.scaffold import scaffold_project_docs  # noqa: E402
from rag.skill_intelligence import (  # noqa: E402
    analyze_skill_candidates,
    apply_skill_proposal,
    create_evolution_proposal,
    create_skill_proposal,
    get_skill_inventory,
    get_skill_proposal,
    run_skill_audit,
    validate_skill_architecture,
)
from rag.project_lifecycle import (  # noqa: E402
    lifecycle_status,
    onboard_project,
    prepare_patch_review,
    pre_publish_status,
    quality_profile,
    record_review,
    verify_patch,
)


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
            "scaffold_project_docs": self.tool_scaffold_project_docs,
            "read_operation_log": self.tool_read_operation_log,
            "analyze_skill_candidates": self.tool_analyze_skill_candidates,
            "get_skill_inventory": self.tool_get_skill_inventory,
            "get_skill_proposal": self.tool_get_skill_proposal,
            "validate_skill_architecture": self.tool_validate_skill_architecture,
            "create_skill_proposal": self.tool_create_skill_proposal,
            "create_skill_evolution_proposal": self.tool_create_skill_evolution_proposal,
            "apply_skill_proposal": self.tool_apply_skill_proposal,
            "get_quality_profile": self.tool_get_quality_profile,
            "prepare_patch_review": self.tool_prepare_patch_review,
            "verify_patch": self.tool_verify_patch,
            "record_code_review": self.tool_record_code_review,
            "record_security_review": self.tool_record_security_review,
            "get_pre_publish_status": self.tool_get_pre_publish_status,
            "onboard_project": self.tool_onboard_project,
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
                "Set configs/projects/*.yaml root to a resolvable external project path."
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

    def tool_scaffold_project_docs(self, args: Json) -> Json:
        project = self.resolve_project(args)
        confirm = bool(args.get("confirm", False))
        fill_empty = bool(args.get("fill_empty", True))
        if not confirm:
            return {
                "requires_confirmation": True,
                "risk": "Scaffolding writes missing documentation files into the connected project root.",
                "safe_default": "No project files were written because confirm=true was not provided.",
                "command": f"make scaffold-docs-write PROJECT={project}",
                "dry_run_command": f"make scaffold-docs PROJECT={project}",
                "mcp_call": {
                    "tool": "scaffold_project_docs",
                    "arguments": {"project": project, "confirm": True, "fill_empty": fill_empty},
                },
            }
        config = get_project_config(project)
        return scaffold_project_docs(config, write=True, fill_empty=fill_empty)

    def tool_read_operation_log(self, args: Json) -> Json:
        project = self.resolve_project(args)
        limit = int(args.get("limit", 20))
        entries = read_operation_log(project, limit=limit)
        return {
            "project": project,
            "log_entries": entries,
            "total_entries": len(entries),
        }

    def tool_analyze_skill_candidates(self, args: Json) -> Json:
        project = self.resolve_project(args)
        report = run_skill_audit(project)
        return {
            "project": report["project"],
            "namespace": report["namespace"],
            "candidates": report["candidates"],
            "classifications": report["classifications"],
            "audited_at": report["audited_at"],
        }

    def tool_get_skill_inventory(self, args: Json) -> Json:
        return get_skill_inventory(self.resolve_project(args))

    def tool_get_skill_proposal(self, args: Json) -> Json:
        project = self.resolve_project(args)
        proposal_id = str(args.get("proposal_id", "")).strip()
        if not proposal_id:
            raise ValueError("proposal_id is required")
        return get_skill_proposal(project, proposal_id)

    def tool_validate_skill_architecture(self, args: Json) -> Json:
        return validate_skill_architecture(self.resolve_project(args))

    def tool_create_skill_proposal(self, args: Json) -> Json:
        project = self.resolve_project(args)
        action = str(args.get("action", "")).strip()
        source_references = args.get("source_references")
        target_paths = args.get("target_paths")
        evidence = args.get("evidence")
        if not isinstance(source_references, list) or not isinstance(target_paths, list) or not isinstance(evidence, list):
            raise ValueError("source_references, target_paths, and evidence must be arrays")
        return create_skill_proposal(
            project,
            action=action,
            source_references=source_references,
            target_paths=target_paths,
            evidence=[str(item) for item in evidence],
            confidence=float(args.get("confidence", 0)),
            reason=str(args.get("reason", "")).strip(),
            constraints=[str(item) for item in args.get("constraints", [])],
            expected_canonical_changes=[
                str(item) for item in args.get("expected_canonical_changes", [])
            ],
            validation_requirements=[
                str(item) for item in args.get("validation_requirements", [])
            ],
        )

    def tool_create_skill_evolution_proposal(self, args: Json) -> Json:
        project = self.resolve_project(args)
        required = ("target_skill_path", "rule", "evidence_type", "evidence_reference")
        missing = [key for key in required if not str(args.get(key, "")).strip()]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")
        return create_evolution_proposal(
            project,
            target_skill_path=str(args["target_skill_path"]),
            rule=str(args["rule"]),
            evidence_type=str(args["evidence_type"]),
            evidence_reference=str(args["evidence_reference"]),
            explicit_user_correction=bool(args.get("explicit_user_correction", False)),
            temporary_workaround=bool(args.get("temporary_workaround", False)),
        )

    def tool_apply_skill_proposal(self, args: Json) -> Json:
        project = self.resolve_project(args)
        proposal_id = str(args.get("proposal_id", "")).strip()
        if not proposal_id:
            raise ValueError("proposal_id is required")
        files = args.get("files")
        if files is not None and (
            not isinstance(files, dict)
            or any(not isinstance(path, str) or not isinstance(content, str) for path, content in files.items())
        ):
            raise ValueError("files must map project-relative paths to reviewed text content")
        return apply_skill_proposal(
            project,
            proposal_id,
            files=files,
            confirm=bool(args.get("confirm", False)),
        )

    def tool_get_quality_profile(self, args: Json) -> Json:
        return quality_profile(self.resolve_project(args))

    def tool_prepare_patch_review(self, args: Json) -> Json:
        return prepare_patch_review(
            self.resolve_project(args),
            kind=str(args.get("kind", "code")),
            scope=str(args.get("scope", "working")),
            base=str(args["base"]) if args.get("base") else None,
        )

    def tool_verify_patch(self, args: Json) -> Json:
        return verify_patch(
            self.resolve_project(args),
            scope=str(args.get("scope", "working")),
            base=str(args["base"]) if args.get("base") else None,
            timeout=float(args.get("timeout", 300)),
        )

    def _record_review(self, args: Json, kind: str) -> Json:
        findings = args.get("findings", [])
        if not isinstance(findings, list):
            raise ValueError("findings must be an array")
        fingerprint = str(args.get("fingerprint", "")).strip()
        if not fingerprint:
            raise ValueError("fingerprint is required")
        return record_review(
            self.resolve_project(args),
            kind=kind,
            scope=str(args.get("scope", "working")),
            base=str(args["base"]) if args.get("base") else None,
            fingerprint=fingerprint,
            status=str(args.get("status", "incomplete")),
            findings=[item for item in findings if isinstance(item, dict)],
            reviewer=str(args.get("reviewer", "codex")),
            summary=str(args.get("summary", "")),
        )

    def tool_record_code_review(self, args: Json) -> Json:
        return self._record_review(args, "code")

    def tool_record_security_review(self, args: Json) -> Json:
        return self._record_review(args, "security")

    def tool_get_pre_publish_status(self, args: Json) -> Json:
        return lifecycle_status(
            self.resolve_project(args),
            scope=str(args.get("scope", "working")),
            base=str(args["base"]) if args.get("base") else None,
        )

    def tool_onboard_project(self, args: Json) -> Json:
        project = self.resolve_project(args)
        if not bool(args.get("confirm", False)):
            return {
                "requires_confirmation": True,
                "risk": "Onboarding may write a compact managed block to the connected project's AGENTS.md and stores metadata only in ignored Hub storage.",
                "safe_default": "No connected project file was changed because confirm=true was not provided.",
                "mcp_call": {"tool": "onboard_project", "arguments": {"project": project, "confirm": True}},
            }
        return onboard_project(project, write=True)

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
                "description": "Return project title, sources, MkDocs adapter state, documentation readiness, agent rules, and index status.",
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
                "name": "scaffold_project_docs",
                "description": "Create missing recommended project documentation files from templates. Requires confirm=true because it writes into the connected project root.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project": project_property,
                        "confirm": {"type": "boolean", "default": False},
                        "fill_empty": {"type": "boolean", "default": True},
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
            {
                "name": "analyze_skill_candidates",
                "description": "Run a deterministic, read-only skill workflow analysis and store its report in local ignored storage.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"project": project_property},
                    "required": [] if self.active_project else ["project"],
                },
            },
            {
                "name": "get_skill_inventory",
                "description": "Inventory project .agents/skills/*/SKILL.md files and their safe metadata.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"project": project_property},
                    "required": [] if self.active_project else ["project"],
                },
            },
            {
                "name": "get_skill_proposal",
                "description": "Read one project-scoped, locally stored Skill Intelligence proposal.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project": project_property,
                        "proposal_id": {"type": "string"},
                    },
                    "required": ["proposal_id"] if self.active_project else ["project", "proposal_id"],
                },
            },
            {
                "name": "validate_skill_architecture",
                "description": "Validate skill frontmatter, references, boundaries, duplicates, and scope without applying changes.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"project": project_property},
                    "required": [] if self.active_project else ["project"],
                },
            },
            {
                "name": "create_skill_proposal",
                "description": "Store a structured project-local proposal for Codex review; does not write project files.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project": project_property,
                        "action": {
                            "type": "string",
                            "enum": [
                                "create_skill", "extend_skill", "refactor_skill", "merge_skills",
                                "split_skill", "move_skill_content_to_docs", "move_agents_content_to_skill",
                                "remove_obsolete_rule", "no_change",
                            ],
                        },
                        "source_references": {"type": "array", "items": {"type": "object"}},
                        "target_paths": {"type": "array", "items": {"type": "string"}},
                        "evidence": {"type": "array", "items": {"type": "string"}},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "reason": {"type": "string"},
                        "constraints": {"type": "array", "items": {"type": "string"}},
                        "expected_canonical_changes": {"type": "array", "items": {"type": "string"}},
                        "validation_requirements": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": (
                        ["action", "source_references", "target_paths", "evidence", "confidence", "reason"]
                        if self.active_project
                        else ["project", "action", "source_references", "target_paths", "evidence", "confidence", "reason"]
                    ),
                },
            },
            {
                "name": "create_skill_evolution_proposal",
                "description": "Propose a reusable skill improvement supported by verified code, regression, test, or explicit user-correction evidence.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project": project_property,
                        "target_skill_path": {"type": "string"},
                        "rule": {"type": "string"},
                        "evidence_type": {
                            "type": "string",
                            "enum": ["working_code", "fixed_regression", "verified_test", "user_correction"],
                        },
                        "evidence_reference": {
                            "type": "string",
                            "description": "Verified project-relative evidence file, or user-correction:<id> for a confirmed correction.",
                        },
                        "explicit_user_correction": {"type": "boolean", "default": False},
                        "temporary_workaround": {"type": "boolean", "default": False},
                    },
                    "required": (
                        ["target_skill_path", "rule", "evidence_type", "evidence_reference"]
                        if self.active_project
                        else ["project", "target_skill_path", "rule", "evidence_type", "evidence_reference"]
                    ),
                },
            },
            {
                "name": "apply_skill_proposal",
                "description": "Apply reviewed replacement text only to proposal-declared project paths; confirm=true is mandatory.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project": project_property,
                        "proposal_id": {"type": "string"},
                        "files": {
                            "type": "object",
                            "additionalProperties": {"type": "string"},
                            "description": "Complete reviewed replacement content keyed by exact proposal target path.",
                        },
                        "confirm": {"type": "boolean", "default": False},
                    },
                    "required": ["proposal_id"] if self.active_project else ["project", "proposal_id"],
                },
            },
            {
                "name": "get_quality_profile",
                "description": "Discover project verification commands and security metadata without running semantic review.",
                "inputSchema": {"type": "object", "properties": {"project": project_property}, "required": [] if self.active_project else ["project"]},
            },
            {
                "name": "prepare_patch_review",
                "description": "Prepare compact diff-first metadata for an explicit code or security review.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project": project_property,
                        "kind": {"type": "string", "enum": ["code", "security"]},
                        "scope": {"type": "string", "enum": ["working", "staged", "range", "branch"], "default": "working"},
                        "base": {"type": "string"},
                    },
                    "required": (["kind"] if self.active_project else ["project", "kind"]),
                },
            },
            {
                "name": "verify_patch",
                "description": "Run deterministic project checks, git diff check and secret scan; stores only local metadata and digests.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project": project_property,
                        "scope": {"type": "string", "enum": ["working", "staged", "range", "branch"], "default": "working"},
                        "base": {"type": "string"},
                        "timeout": {"type": "number", "default": 300},
                    },
                    "required": [] if self.active_project else ["project"],
                },
            },
            {
                "name": "record_code_review",
                "description": "Record an explicit semantic code review tied to the current patch fingerprint.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project": project_property, "scope": {"type": "string"}, "base": {"type": "string"},
                        "fingerprint": {"type": "string"}, "status": {"type": "string", "enum": ["passed", "failed", "incomplete"]},
                        "findings": {"type": "array", "items": {"type": "object"}}, "summary": {"type": "string"}, "reviewer": {"type": "string"},
                    },
                    "required": (["fingerprint", "status"] if self.active_project else ["project", "fingerprint", "status"]),
                },
            },
            {
                "name": "record_security_review",
                "description": "Record a separate adaptive security review tied to the current patch fingerprint; never asserts absolute security.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project": project_property, "scope": {"type": "string"}, "base": {"type": "string"},
                        "fingerprint": {"type": "string"}, "status": {"type": "string", "enum": ["passed", "failed", "incomplete"]},
                        "findings": {"type": "array", "items": {"type": "object"}}, "summary": {"type": "string"}, "reviewer": {"type": "string"},
                    },
                    "required": (["fingerprint", "status"] if self.active_project else ["project", "fingerprint", "status"]),
                },
            },
            {
                "name": "get_pre_publish_status",
                "description": "Return current lifecycle state and whether the exact patch is publishable.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"project": project_property, "scope": {"type": "string"}, "base": {"type": "string"}},
                    "required": [] if self.active_project else ["project"],
                },
            },
            {
                "name": "onboard_project",
                "description": "Safely add or refresh only the Hub-managed lifecycle block in project AGENTS.md; confirm=true is mandatory.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"project": project_property, "confirm": {"type": "boolean", "default": False}},
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
