from __future__ import annotations

import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rag.claude_code import (
    HUB_SERVER,
    ClaudeConfigError,
    claude_mcp_status,
    codebase_server_name,
    configure_claude_mcp,
    desired_servers,
    docs_server_name,
)
from rag.config import HUB_ROOT, ProjectConfig


def make_config(root: Path) -> ProjectConfig:
    return ProjectConfig(
        project="synthetic-claude",
        namespace="synthetic-claude",
        title="Synthetic",
        root=root,
        root_source="${AI_DOCS_PROJECTS_ROOT}/synthetic",
        docs_backend="standard",
        mkdocs_config="mkdocs.yml",
        sources=[],
        include=["docs/**/*.md"],
        exclude=[],
        agent_rules=[],
        config_path=root / "project.yaml",
        raw={},
    )


class ClaudeCodeMcpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        base = Path(self.directory.name)
        self.home = base / "home"
        self.home.mkdir()
        self.root = base / "synthetic"
        self.root.mkdir()
        self.config_file = self.home / ".claude.json"
        self.patches = [
            patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(self.home), "CODEBASE_MEMORY_BIN": str(base / "missing-bin")}, clear=False),
            patch("rag.claude_code.get_project_config", return_value=make_config(self.root)),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self) -> None:
        for item in reversed(self.patches):
            item.stop()
        self.directory.cleanup()

    def read(self) -> dict:
        return json.loads(self.config_file.read_text(encoding="utf-8"))

    def test_dry_run_does_not_write(self) -> None:
        result = configure_claude_mcp("synthetic-claude")
        self.assertFalse(self.config_file.exists())
        self.assertEqual(result["changes"], ["set synthetic_claude_docs"])
        self.assertFalse(result["configured"])
        self.assertFalse(result["restart_required"])

    def test_write_preserves_unrelated_config_and_servers(self) -> None:
        other = {"type": "stdio", "command": "node", "args": ["other.js"]}
        self.config_file.write_text(json.dumps({"oauthAccount": {"x": 1}, "projects": {str(self.root.resolve()): {"allowedTools": ["a"], "mcpServers": {"other": other}}}}), encoding="utf-8")
        os.chmod(self.config_file, 0o600)
        result = configure_claude_mcp("synthetic-claude", write=True)
        data = self.read()
        self.assertTrue(result["configured"])
        self.assertTrue(result["restart_required"])
        self.assertEqual(data["oauthAccount"], {"x": 1})
        settings = data["projects"][str(self.root.resolve())]
        self.assertEqual(settings["allowedTools"], ["a"])
        self.assertEqual(settings["mcpServers"]["other"], other)
        server = settings["mcpServers"][docs_server_name("synthetic-claude")]
        self.assertEqual(server["args"], [str(HUB_ROOT / "mcp" / "server.py"), "--project", "synthetic-claude"])
        self.assertEqual(stat.S_IMODE(self.config_file.stat().st_mode), 0o600)
        again = configure_claude_mcp("synthetic-claude", write=True)
        self.assertEqual(again["changes"], [])
        self.assertFalse(again["restart_required"])

    def test_foreign_same_name_server_is_not_replaced(self) -> None:
        foreign = {"type": "stdio", "command": "python", "args": ["/elsewhere/server.py"]}
        self.config_file.write_text(json.dumps({"projects": {str(self.root.resolve()): {"mcpServers": {"synthetic_claude_docs": foreign}}}}), encoding="utf-8")
        result = configure_claude_mcp("synthetic-claude", write=True)
        self.assertEqual(self.read()["projects"][str(self.root.resolve())]["mcpServers"]["synthetic_claude_docs"], foreign)
        self.assertEqual(result["servers"]["synthetic_claude_docs"], "foreign")
        self.assertFalse(result["configured"])

    def test_remove_only_drops_hub_entries(self) -> None:
        configure_claude_mcp("synthetic-claude", write=True)
        data = self.read()
        data["projects"][str(self.root.resolve())]["mcpServers"]["other"] = {"command": "node", "args": ["x.js"]}
        self.config_file.write_text(json.dumps(data), encoding="utf-8")
        configure_claude_mcp("synthetic-claude", write=True, remove=True)
        self.assertEqual(list(self.read()["projects"][str(self.root.resolve())]["mcpServers"]), ["other"])

    def test_codebase_server_only_when_binary_and_graph_present(self) -> None:
        base = Path(self.directory.name)
        binary, cache = base / "cbm-bin", base / "cbm-cache"
        cache.mkdir()
        binary.write_text("", encoding="utf-8")
        with patch.dict(os.environ, {"CODEBASE_MEMORY_BIN": str(binary), "CBM_CACHE_DIR": str(cache)}):
            self.assertNotIn(codebase_server_name("synthetic-claude"), desired_servers("synthetic-claude"))
            (cache / "synthetic-claude.db").write_text("", encoding="utf-8")
            self.assertIn(codebase_server_name("synthetic-claude"), desired_servers("synthetic-claude"))
        servers = desired_servers("synthetic-claude", codebase_memory=True)
        self.assertEqual(servers[codebase_server_name("synthetic-claude")]["args"][1:], ["--project", "synthetic-claude"])
        self.assertIn("CBM_CACHE_DIR", servers[codebase_server_name("synthetic-claude")]["env"])

    def test_hub_target_uses_unscoped_server(self) -> None:
        result = configure_claude_mcp(None, write=True)
        self.assertEqual(result["claude_project_dir"], str(HUB_ROOT.resolve()))
        self.assertEqual(self.read()["projects"][str(HUB_ROOT.resolve())]["mcpServers"][HUB_SERVER]["args"], [str(HUB_ROOT / "mcp" / "server.py")])
        self.assertTrue(claude_mcp_status(None)["configured"])

    def test_invalid_json_is_never_overwritten(self) -> None:
        self.config_file.write_text("{broken", encoding="utf-8")
        with self.assertRaises(ClaudeConfigError):
            configure_claude_mcp("synthetic-claude", write=True)
        self.assertEqual(self.config_file.read_text(encoding="utf-8"), "{broken")

    def test_hub_checkout_cannot_be_a_connected_project(self) -> None:
        with patch("rag.claude_code.get_project_config", return_value=make_config(HUB_ROOT)):
            with self.assertRaises(ClaudeConfigError):
                configure_claude_mcp("synthetic-claude")


if __name__ == "__main__":
    unittest.main()
