from __future__ import annotations

import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rag.config import HUB_ROOT, ProjectConfig
from rag.kimi_code import (
    HUB_SERVER,
    KimiConfigError,
    codebase_server_name,
    configure_kimi_mcp,
    desired_servers,
    docs_server_name,
    kimi_config_path,
    kimi_mcp_status,
)


def make_config(root: Path) -> ProjectConfig:
    return ProjectConfig(
        project="synthetic-kimi",
        namespace="synthetic-kimi",
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


class KimiCodeMcpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        base = Path(self.directory.name)
        self.home = base / "kimi-home"
        self.home.mkdir()
        self.root = base / "synthetic"
        self.root.mkdir()
        self.config_file = self.home / "mcp.json"
        self.patches = [
            patch.dict(os.environ, {"KIMI_CODE_HOME": str(self.home), "CODEBASE_MEMORY_BIN": str(base / "missing-bin")}, clear=False),
            patch("rag.kimi_code.get_project_config", return_value=make_config(self.root)),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self) -> None:
        for item in reversed(self.patches):
            item.stop()
        self.directory.cleanup()

    def read(self) -> dict:
        return json.loads(self.config_file.read_text(encoding="utf-8"))

    def test_config_path_honors_kimi_code_home(self) -> None:
        self.assertEqual(kimi_config_path(), self.config_file)
        with patch.dict(os.environ, {"KIMI_CODE_HOME": ""}, clear=False):
            self.assertEqual(kimi_config_path(), Path.home() / ".kimi-code" / "mcp.json")

    def test_dry_run_does_not_write(self) -> None:
        result = configure_kimi_mcp("synthetic-kimi")
        self.assertFalse(self.config_file.exists())
        self.assertEqual(result["changes"], ["set synthetic_kimi_docs"])
        self.assertFalse(result["configured"])
        self.assertFalse(result["restart_required"])

    def test_write_preserves_unrelated_config_and_servers(self) -> None:
        other = {"command": "node", "args": ["other.js"]}
        self.config_file.write_text(json.dumps({"theme": "dark", "mcpServers": {"other": other}}), encoding="utf-8")
        os.chmod(self.config_file, 0o600)
        result = configure_kimi_mcp("synthetic-kimi", write=True)
        data = self.read()
        self.assertTrue(result["configured"])
        self.assertTrue(result["restart_required"])
        self.assertEqual(data["theme"], "dark")
        self.assertEqual(data["mcpServers"]["other"], other)
        server = data["mcpServers"][docs_server_name("synthetic-kimi")]
        self.assertNotIn("type", server)
        self.assertEqual(server["args"], [str(HUB_ROOT / "mcp" / "server.py"), "--project", "synthetic-kimi"])
        self.assertEqual(stat.S_IMODE(self.config_file.stat().st_mode), 0o600)
        again = configure_kimi_mcp("synthetic-kimi", write=True)
        self.assertEqual(again["changes"], [])
        self.assertFalse(again["restart_required"])

    def test_foreign_same_name_server_is_not_replaced(self) -> None:
        foreign = {"command": "python", "args": ["/elsewhere/server.py"]}
        self.config_file.write_text(json.dumps({"mcpServers": {"synthetic_kimi_docs": foreign}}), encoding="utf-8")
        result = configure_kimi_mcp("synthetic-kimi", write=True)
        self.assertEqual(self.read()["mcpServers"]["synthetic_kimi_docs"], foreign)
        self.assertEqual(result["servers"]["synthetic_kimi_docs"], "foreign")
        self.assertFalse(result["configured"])

    def test_remove_only_drops_hub_entries_of_target_project(self) -> None:
        configure_kimi_mcp("synthetic-kimi", write=True)
        data = self.read()
        data["mcpServers"]["other_project_docs"] = {
            "command": "python",
            "args": [str(HUB_ROOT / "mcp" / "server.py"), "--project", "other-project"],
        }
        data["mcpServers"]["other"] = {"command": "node", "args": ["x.js"]}
        self.config_file.write_text(json.dumps(data), encoding="utf-8")
        configure_kimi_mcp("synthetic-kimi", write=True, remove=True)
        self.assertEqual(sorted(self.read()["mcpServers"]), ["other", "other_project_docs"])

    def test_codebase_server_only_when_binary_and_graph_present(self) -> None:
        base = Path(self.directory.name)
        binary, cache = base / "cbm-bin", base / "cbm-cache"
        cache.mkdir()
        binary.write_text("", encoding="utf-8")
        with patch.dict(os.environ, {"CODEBASE_MEMORY_BIN": str(binary), "CBM_CACHE_DIR": str(cache)}):
            self.assertNotIn(codebase_server_name("synthetic-kimi"), desired_servers("synthetic-kimi"))
            (cache / "synthetic-kimi.db").write_text("", encoding="utf-8")
            self.assertIn(codebase_server_name("synthetic-kimi"), desired_servers("synthetic-kimi"))
        servers = desired_servers("synthetic-kimi", codebase_memory=True)
        self.assertEqual(servers[codebase_server_name("synthetic-kimi")]["args"][1:], ["--project", "synthetic-kimi"])
        self.assertIn("CBM_CACHE_DIR", servers[codebase_server_name("synthetic-kimi")]["env"])

    def test_hub_target_uses_unscoped_server(self) -> None:
        result = configure_kimi_mcp(None, write=True)
        self.assertEqual(self.read()["mcpServers"][HUB_SERVER]["args"], [str(HUB_ROOT / "mcp" / "server.py")])
        self.assertTrue(kimi_mcp_status(None)["configured"])

    def test_project_and_hub_entries_share_one_file(self) -> None:
        configure_kimi_mcp(None, write=True)
        result = configure_kimi_mcp("synthetic-kimi", write=True)
        servers = self.read()["mcpServers"]
        self.assertIn(HUB_SERVER, servers)
        self.assertIn(docs_server_name("synthetic-kimi"), servers)
        self.assertTrue(result["configured"])
        self.assertTrue(kimi_mcp_status(None)["configured"])

    def test_invalid_json_is_never_overwritten(self) -> None:
        self.config_file.write_text("{broken", encoding="utf-8")
        with self.assertRaises(KimiConfigError):
            configure_kimi_mcp("synthetic-kimi", write=True)
        self.assertEqual(self.config_file.read_text(encoding="utf-8"), "{broken")

    def test_hub_checkout_cannot_be_a_connected_project(self) -> None:
        with patch("rag.kimi_code.get_project_config", return_value=make_config(HUB_ROOT)):
            with self.assertRaises(KimiConfigError):
                configure_kimi_mcp("synthetic-kimi")


if __name__ == "__main__":
    unittest.main()
