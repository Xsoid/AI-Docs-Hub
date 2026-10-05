from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from mcp.server import McpServer
from rag.mcp_audit import CODEBASE_SERVER, audit_tool_call, usage_summary, write_event


class McpAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.audit_dir = Path(self.directory.name) / "audit"
        self.env = patch.dict(os.environ, {"MCP_AUDIT_DIR": str(self.audit_dir)}, clear=False)
        self.env.start()

    def tearDown(self) -> None:
        self.env.stop()
        self.directory.cleanup()

    def events(self) -> list[dict]:
        paths = sorted(self.audit_dir.glob("*.jsonl"))
        return [json.loads(line) for path in paths for line in path.read_text(encoding="utf-8").splitlines() if line]

    def test_sanitized_success_event_and_confirm_allowlist(self) -> None:
        with audit_tool_call(
            server="local-ai-docs-hub",
            project="audit-project",
            tool="index_project",
            arguments={"confirm": True, "query": "private search", "source_path": "/private/project/doc.md"},
        ) as audit:
            audit.finish(result={"content": "secret document", "token": "never"})
        event = self.events()[0]
        raw = json.dumps(event, ensure_ascii=False)
        self.assertEqual(event["project"], "audit-project")
        self.assertEqual(event["metadata"], {"confirm": True})
        self.assertGreaterEqual(event["duration_ms"], 0)
        self.assertNotIn("private search", raw)
        self.assertNotIn("/private/project/doc.md", raw)
        self.assertNotIn("secret document", raw)
        self.assertNotIn("never", raw)

    def test_exception_logs_category_without_message(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "absolute /private path"):
            with audit_tool_call(server=CODEBASE_SERVER, project="audit-project", tool="search_code", arguments={"query": "password"}):
                raise RuntimeError("absolute /private path and password=super-secret")
        event = self.events()[0]
        self.assertEqual(event["status"], "error")
        self.assertEqual(event["error_category"], "RuntimeError")
        raw = json.dumps(event, ensure_ascii=False)
        self.assertNotIn("absolute", raw)
        self.assertNotIn("super-secret", raw)
        self.assertNotIn("password", raw)

    def test_server_success_and_error_calls_are_audited(self) -> None:
        server = McpServer(active_project="audit-project")
        server.tools["synthetic_read"] = lambda args: {"ok": True}
        server.tools["synthetic_error"] = lambda args: (_ for _ in ()).throw(ValueError("path /private and query=hidden"))
        success = server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "synthetic_read", "arguments": {}}})
        failure = server.handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "synthetic_error", "arguments": {}}})
        self.assertFalse(success["result"]["isError"])
        self.assertTrue(failure["result"]["isError"])
        events = self.events()
        self.assertEqual([event["status"] for event in events], ["ok", "error"])
        self.assertEqual(events[0]["project"], "audit-project")
        self.assertEqual(events[1]["error_category"], "ValueError")
        self.assertNotIn("/private", json.dumps(events))

    def test_unknown_tool_and_client_metadata_are_sanitized(self) -> None:
        server = McpServer(active_project="audit-project")
        server.client_info = "/private/client/1"
        response = server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "/private/tool", "arguments": {}}})
        self.assertEqual(response["error"]["code"], -32602)
        event = self.events()[0]
        self.assertEqual(event["status"], "error")
        self.assertEqual(event["tool"], "unknown")
        self.assertEqual(event["client"], "private-client-1")
        self.assertNotIn("/private", json.dumps(event))

    def test_audit_write_failure_does_not_change_tool_response(self) -> None:
        server = McpServer(active_project="audit-project")
        server.tools["synthetic_read"] = lambda args: {"ok": True}
        with patch("rag.mcp_audit.write_event", side_effect=OSError("disk unavailable")):
            response = server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "synthetic_read", "arguments": {}}})
        self.assertFalse(response["result"]["isError"])

    def test_summary_counts_projects_servers_and_ignores_summary_recursion(self) -> None:
        write_event({"schema_version": 1, "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "server": "local-ai-docs-hub", "transport": "stdio", "project": "audit-project", "tool": "search_docs", "tool_class": "read", "duration_ms": 2, "status": "ok", "is_error": False, "result_size_bytes": 10})
        write_event({"schema_version": 1, "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "server": CODEBASE_SERVER, "transport": "stdio", "project": "audit-project", "tool": "search_code", "tool_class": "read", "duration_ms": 3, "status": "error", "is_error": True, "result_size_bytes": 0, "error_category": "ValueError"})
        write_event({"schema_version": 1, "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "server": "local-ai-docs-hub", "transport": "stdio", "project": "audit-project", "tool": "get_mcp_usage_summary", "tool_class": "read", "duration_ms": 1, "status": "ok", "is_error": False, "result_size_bytes": 20})
        summary = usage_summary(project="audit-project", window_hours=24)
        self.assertEqual(summary["calls"], 2)
        self.assertEqual(summary["errors"], 1)
        self.assertEqual(summary["tools"]["search_docs"], {"calls": 1, "errors": 0})
        self.assertEqual(summary["tools"]["search_code"], {"calls": 1, "errors": 1})
        self.assertEqual(summary["servers"][CODEBASE_SERVER], 1)

    def test_corrupt_lines_are_ignored_and_retention_is_bounded(self) -> None:
        self.audit_dir.mkdir(parents=True)
        old = (datetime.now(timezone.utc) - timedelta(days=3)).date().isoformat()
        (self.audit_dir / f"{old}.jsonl").write_text("not json\n", encoding="utf-8")
        with patch.dict(os.environ, {"MCP_AUDIT_RETENTION_DAYS": "2"}, clear=False):
            write_event({"schema_version": 1, "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "server": "local-ai-docs-hub", "tool": "healthcheck", "is_error": False})
            summary = usage_summary(window_hours=24)
        self.assertFalse((self.audit_dir / f"{old}.jsonl").exists())
        self.assertEqual(summary["calls"], 1)


if __name__ == "__main__":
    unittest.main()
