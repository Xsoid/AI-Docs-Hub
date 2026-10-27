from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from mcp.server import McpServer
from rag.config import ProjectConfig
from rag.decision_engine import REGISTRY as DECISION_REGISTRY
from rag.project_context import (
    MANIFEST_BUDGET_BYTES,
    MAX_INSTRUCTION_FILES,
    build_project_context,
    discover_project_instructions,
    read_project_instruction,
)


def make_config(root: Path, project: str = "context-project") -> ProjectConfig:
    return ProjectConfig(
        project=project,
        namespace=project,
        title="Context Project",
        root=root,
        root_source=str(root),
        docs_backend="standard",
        mkdocs_config="mkdocs.yml",
        sources=[{"path": "README.md", "type": "markdown"}],
        include=["README.md"],
        exclude=[".git/**", "node_modules/**", "vendor/**", "storage/**", "tmp/**"],
        agent_rules=[],
        config_path=root / "project.yaml",
        raw={"exclude": [".git/**", "node_modules/**", "vendor/**", "storage/**", "tmp/**"]},
        schema_version=1,
    )


class ProjectContextTests(unittest.TestCase):
    def test_discovers_root_and_nested_instructions_deterministically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("Project overview", encoding="utf-8")
            (root / "AGENTS.md").write_text("root rules", encoding="utf-8")
            (root / "src" / "Billing").mkdir(parents=True)
            (root / "src" / "Billing" / "AGENTS.MD").write_text("billing rules", encoding="utf-8")
            (root / "src" / "CLAUDE.md").write_text("claude rules", encoding="utf-8")
            (root / "node_modules" / "nested").mkdir(parents=True)
            (root / "node_modules" / "nested" / "AGENTS.md").write_text("excluded", encoding="utf-8")

            first = discover_project_instructions(make_config(root))
            second = discover_project_instructions(make_config(root))
            self.assertEqual(first, second)
            self.assertEqual([item["path"] for item in first["items"]], ["AGENTS.md", "src/Billing/AGENTS.MD", "src/CLAUDE.md"])
            self.assertEqual(first["items"][1]["scope"], "src/Billing")
            self.assertNotIn("root rules", json.dumps(first))

    def test_symlink_escape_and_excluded_directories_are_not_discovered(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside_directory:
            root = Path(directory)
            outside = Path(outside_directory) / "AGENTS.md"
            outside.write_text("outside", encoding="utf-8")
            (root / "README.md").write_text("overview", encoding="utf-8")
            (root / "linked").mkdir()
            try:
                os.symlink(outside, root / "linked" / "AGENTS.md")
            except OSError:
                self.skipTest("symlinks are unavailable")
            (root / ".git").mkdir()
            (root / ".git" / "AGENTS.md").write_text("excluded", encoding="utf-8")
            paths = [item["path"] for item in discover_project_instructions(make_config(root))["items"]]
            self.assertNotIn("linked/AGENTS.md", paths)
            self.assertNotIn(".git/AGENTS.md", paths)

    def test_discovery_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("overview", encoding="utf-8")
            for index in range(MAX_INSTRUCTION_FILES + 5):
                nested = root / "instructions" / str(index)
                nested.mkdir(parents=True)
                (nested / "AGENTS.md").write_text(str(index), encoding="utf-8")
            result = discover_project_instructions(make_config(root))
            self.assertEqual(result["count"], MAX_INSTRUCTION_FILES)
            self.assertTrue(result["truncated"])

    def test_read_is_on_demand_scoped_and_secret_checked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("source content that must not be preloaded", encoding="utf-8")
            (root / "AGENTS.md").write_text("safe rules", encoding="utf-8")
            (root / "secret").mkdir()
            (root / "secret" / "CLAUDE.md").write_text("token = 'supersecretvalue'", encoding="utf-8")
            config = make_config(root)
            context = build_project_context(config)
            self.assertNotIn("source content that must not be preloaded", json.dumps(context))
            self.assertEqual(read_project_instruction(config, "AGENTS.md")["content"], "safe rules")
            with self.assertRaises(PermissionError):
                read_project_instruction(config, "README.md")
            with self.assertRaises(PermissionError):
                read_project_instruction(config, "../outside.md")
            with self.assertRaises(PermissionError):
                read_project_instruction(config, "secret/CLAUDE.md")

    def test_manifest_aggregates_missing_index_skills_and_is_project_scoped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("overview", encoding="utf-8")
            skill = root / ".agents" / "skills" / "ui-review"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("---\nname: ui-review\ndescription: Review UI\n---\n# UI\n", encoding="utf-8")
            config = make_config(root)
            context = build_project_context(config)
            self.assertEqual(context["documentation"]["status"], "missing")
            self.assertEqual(context["documentation"]["recommendation"], "index_project")
            self.assertEqual(context["skills"][0]["name"], "ui-review")
            self.assertFalse(context["skill_discovery"]["truncated"])
            self.assertNotIn("# UI", json.dumps(context))
            self.assertIn("get_project_context", [tool["name"] for tool in McpServer(active_project="context-project").tool_specs()])
            response = McpServer(active_project="context-project").handle_request({
                "id": 1,
                "method": "tools/call",
                "params": {"name": "get_project_context", "arguments": {"project": "other-project"}},
            })
            self.assertTrue(response["result"]["isError"])

    def test_manifest_of_a_large_typical_project_fits_the_budget(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for folder in ("", "app", "infra"):
                (root / folder).mkdir(exist_ok=True)
                (root / folder / "AGENTS.md").write_text("rules", encoding="utf-8")
                (root / folder / "CLAUDE.md").write_text("rules", encoding="utf-8")
            for number in range(15):
                skill = root / ".agents" / "skills" / f"workflow-{number:02d}"
                skill.mkdir(parents=True)
                (skill / "SKILL.md").write_text(f"---\nname: workflow-{number:02d}\ndescription: {'Описание процесса. ' * 15}\n---\n# Body\n", encoding="utf-8")

            context = build_project_context(make_config(root))

            self.assertEqual(context["skill_discovery"]["count"], 15)
            self.assertEqual(context["instruction_discovery"]["count"], 6)
            self.assertLessEqual(len(json.dumps(context, ensure_ascii=False).encode("utf-8")), MANIFEST_BUDGET_BYTES)

    def test_manifest_lists_skills_and_decisions_compactly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill = root / ".agents" / "skills" / "ui-review"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("---\nname: ui-review\ndescription: Review UI\n---\n# UI\n", encoding="utf-8")

            context = build_project_context(make_config(root))

            self.assertEqual(context["skills"], [{"name": "ui-review", "path": ".agents/skills/ui-review/SKILL.md"}])
            self.assertEqual(set(context["decision_engine"]), {"mode", "decisions"})
            self.assertEqual(context["decision_engine"]["mode"], "shadow")
            self.assertEqual(context["decision_engine"]["decisions"]["context.docs_ready"], False)
            self.assertIn(context["decision_engine"]["decisions"]["context.primary_sources"], DECISION_REGISTRY["context.primary_sources"].allowed_values)


if __name__ == "__main__":
    unittest.main()
