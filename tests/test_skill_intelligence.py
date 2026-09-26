from __future__ import annotations

import contextlib
from importlib.machinery import SourceFileLoader
import importlib.util
import io
import subprocess
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rag.config import ProjectConfig
from rag.skill_intelligence import (
    analyze_skill_candidates,
    apply_skill_proposal,
    create_evolution_proposal,
    create_skill_proposal,
    get_skill_inventory,
    run_skill_audit,
    validate_skill_architecture,
)
from mcp.server import McpServer


def make_project(root: Path) -> ProjectConfig:
    return ProjectConfig(
        project="synthetic-project",
        namespace="synthetic-project",
        title="Synthetic Project",
        root=root,
        root_source="<SYNTHETIC_PROJECT_ROOT>",
        docs_backend="standard",
        mkdocs_config="mkdocs.yml",
        sources=[],
        include=["docs/**/*.md"],
        exclude=[],
        agent_rules=[],
        config_path=root / "project.yaml",
        raw={},
    )


class SkillIntelligenceIsolationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.base = Path(self.temp_dir.name)
        self.project_root = self.base / "external-project"
        (self.project_root / "docs").mkdir(parents=True)
        (self.project_root / ".agents" / "skills" / "deploy").mkdir(parents=True)
        (self.project_root / "docs" / "workflow.md").write_text(
            "# Deployment Workflow\n\n"
            "Before changing deployment, first check the deployment docs.\n"
            "1. Run the validation command.\n"
            "2. Verify the result and update the runbook.\n",
            encoding="utf-8",
        )
        (self.project_root / "AGENTS.md").write_text(
            "# Agent Rules\n\nProduction changes are prohibited without explicit approval.\n",
            encoding="utf-8",
        )
        (self.project_root / "unrelated.txt").write_text("Preserve this file unchanged.\n", encoding="utf-8")
        (self.project_root / ".agents" / "skills" / "deploy" / "SKILL.md").write_text(
            "---\nname: deploy\ndescription: Deploy the project safely.\n---\n"
            "# Deploy\n\nSee [deployment docs](../../../docs/workflow.md).\n",
            encoding="utf-8",
        )
        self.config = make_project(self.project_root)
        self.storage = self.base / "hub" / "storage" / "skill-intelligence"
        self.hub_root = self.base / "hub"
        self.hub_root.mkdir()
        (self.hub_root / ".gitignore").write_text("storage/*\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(self.hub_root)], check=True)
        (self.hub_root / "docs").mkdir()
        (self.hub_root / "docs" / "policy.md").write_text("Canonical Hub policy.\n", encoding="utf-8")
        (self.hub_root / "docs-site" / "content").mkdir(parents=True)
        (self.hub_root / "docs-site" / "content" / "policy.md").write_text(
            "Mirrored Hub policy.\n", encoding="utf-8"
        )
        (self.hub_root / "docs" / "changes").mkdir()
        (self.hub_root / "docs" / "changes" / "note.md").write_text(
            "Hub change note.\n", encoding="utf-8"
        )
        subprocess.run(
            ["git", "-C", str(self.hub_root), "config", "user.email", "test@example.invalid"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.hub_root), "config", "user.name", "Synthetic Test"],
            check=True,
        )
        subprocess.run(["git", "-C", str(self.hub_root), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(self.hub_root), "commit", "-qm", "synthetic baseline"], check=True)

    def hub_status(self) -> str:
        return subprocess.check_output(
            ["git", "-C", str(self.hub_root), "status", "--short"],
            text=True,
        )

    def test_inventory_and_audit_read_synthetic_external_project(self) -> None:
        status_before = self.hub_status()
        with patch("rag.skill_intelligence.HUB_ROOT", self.hub_root), patch(
            "rag.skill_intelligence.SKILL_STORAGE_DIR", self.storage
        ), patch("rag.skill_intelligence.log_operation"):
            inventory = get_skill_inventory(self.config)
            audit = run_skill_audit(self.config)
            candidates = analyze_skill_candidates(self.config)

        self.assertEqual(inventory["count"], 1)
        self.assertEqual(inventory["skills"][0]["name"], "deploy")
        self.assertTrue(audit["candidates"])
        self.assertIn("source_excerpt", candidates["candidates"][0])
        self.assertTrue(
            any(item["classification"] == "global_guardrail" for item in candidates["classifications"])
        )
        self.assertTrue(
            any(item["classification"] == "global_guardrail" for item in audit["classifications"])
        )
        self.assertTrue((self.storage / "synthetic-project" / "audit.json").is_file())
        self.assertEqual(self.hub_status(), status_before)

    def test_validator_reports_secret_duplicates_scope_and_broken_links(self) -> None:
        duplicate_dir = self.project_root / ".agents" / "skills" / "duplicate"
        duplicate_dir.mkdir()
        (duplicate_dir / "SKILL.md").write_text(
            "---\nname: deploy\ndescription: Duplicate skill.\n---\n"
            "# Router\n\nRoute requests to [missing](./not-found.md).\n"
            f"See `{(self.base / 'local-path.md').as_posix()}` for details.\n",
            encoding="utf-8",
        )
        secret_dir = self.project_root / ".agents" / "skills" / "unsafe"
        secret_dir.mkdir()
        (secret_dir / "SKILL.md").write_text(
            "---\nname: unsafe\ndescription: Synthetic secret fixture.\n---\n"
            "api_key=synthetic-not-a-real-key\n",
            encoding="utf-8",
        )
        with patch("rag.skill_intelligence.log_operation"):
            report = validate_skill_architecture(self.config)

        issue_types = {issue["type"] for issue in report["issues"]}
        self.assertIn("duplicate_skill_name", issue_types)
        self.assertIn("secret_content", issue_types)
        self.assertIn("broken_reference", issue_types)
        self.assertIn("absolute_path", issue_types)
        self.assertIn("router_skill", issue_types)
        self.assertEqual(report["status"], "blocked")

    def test_proposal_apply_is_confirmed_and_confined_to_external_project(self) -> None:
        status_before = self.hub_status()
        project_files_before = {
            path.relative_to(self.project_root).as_posix(): path.read_bytes()
            for path in self.project_root.rglob("*")
            if path.is_file()
        }
        skill_path = ".agents/skills/new-workflow/SKILL.md"
        skill_content = (
            "---\nname: new-workflow\ndescription: Run the reviewed workflow.\n---\n"
            "# Workflow\n\nFollow the documented project procedure.\n"
        )
        with patch("rag.skill_intelligence.HUB_ROOT", self.hub_root), patch(
            "rag.skill_intelligence.SKILL_STORAGE_DIR", self.storage
        ), patch("rag.skill_intelligence.log_operation"):
            proposal = create_skill_proposal(
                self.config,
                action="create_skill",
                source_references=[{"source_path": "docs/workflow.md", "heading": "Deployment Workflow"}],
                target_paths=[skill_path],
                evidence=["ordered_steps"],
                confidence=0.8,
                reason="Synthetic repeatable workflow.",
            )
            dry_run = apply_skill_proposal(
                self.config,
                proposal["proposal_id"],
                files={skill_path: skill_content},
            )
            self.assertTrue(dry_run["requires_confirmation"])
            target = self.project_root / skill_path
            self.assertFalse(target.exists())

            result = apply_skill_proposal(
                self.config,
                proposal["proposal_id"],
                files={skill_path: skill_content},
                confirm=True,
            )

        self.assertTrue(result["applied"])
        self.assertEqual(target.read_text(encoding="utf-8"), skill_content)
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o644)
        self.assertFalse((self.hub_root / skill_path).exists())
        self.assertEqual(self.hub_status(), status_before)
        project_files_after = {
            path.relative_to(self.project_root).as_posix(): path.read_bytes()
            for path in self.project_root.rglob("*")
            if path.is_file()
        }
        self.assertEqual(
            set(project_files_after) - set(project_files_before),
            {skill_path},
        )
        self.assertTrue(
            all(project_files_after[path] == value for path, value in project_files_before.items())
        )
        self.assertTrue((self.storage / "synthetic-project" / "proposals" / f"{proposal['proposal_id']}.json").is_file())
        ignored = subprocess.run(
            ["git", "-C", str(self.hub_root), "check-ignore", "-q", "storage/skill-intelligence/synthetic-project/audit.json"],
            check=False,
        )
        self.assertEqual(ignored.returncode, 0)

    def test_evolution_proposal_requires_verified_evidence_and_never_applies(self) -> None:
        with patch("rag.skill_intelligence.HUB_ROOT", self.hub_root), patch(
            "rag.skill_intelligence.SKILL_STORAGE_DIR", self.storage
        ), patch("rag.skill_intelligence.log_operation"):
            proposal = create_evolution_proposal(
                self.config,
                target_skill_path=".agents/skills/deploy/SKILL.md",
                rule="Check the deployment validation result before promotion.",
                evidence_type="user_correction",
                evidence_reference="user-correction:synthetic-001",
                explicit_user_correction=True,
            )
            self.assertEqual(proposal["confidence"], 0.95)
            self.assertEqual(proposal["action"], "extend_skill")
            with self.assertRaises(ValueError):
                create_evolution_proposal(
                    self.config,
                    target_skill_path=".agents/skills/deploy/SKILL.md",
                    rule="Temporary rule.",
                    evidence_type="verified_test",
                    evidence_reference="docs/workflow.md",
                    temporary_workaround=True,
                )

    def test_mcp_skill_tools_are_project_scoped_and_have_confirmation_default(self) -> None:
        server = McpServer(active_project="synthetic-project")
        names = {tool["name"]: tool for tool in server.tool_specs()}
        self.assertTrue(
            {
                "analyze_skill_candidates",
                "get_skill_inventory",
                "get_skill_proposal",
                "validate_skill_architecture",
                "create_skill_proposal",
                "apply_skill_proposal",
            }.issubset(names)
        )
        apply_schema = names["apply_skill_proposal"]["inputSchema"]
        self.assertFalse(apply_schema["properties"]["confirm"]["default"])
        with self.assertRaises(PermissionError):
            server.resolve_project({"project": "another-project"})

    def test_skill_audit_cli_outputs_human_and_json_reports(self) -> None:
        script = Path(__file__).resolve().parents[1] / "scripts" / "skill-audit"
        loader = SourceFileLoader("skill_audit_cli", str(script))
        spec = importlib.util.spec_from_loader("skill_audit_cli", loader)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        report = {
            "project": "synthetic-project",
            "namespace": "synthetic-project",
            "status": "ok",
            "skills": {"skills": [{"name": "deploy", "path": ".agents/skills/deploy/SKILL.md"}]},
            "candidates": [
                {
                    "source_path": "docs/workflow.md",
                    "start_line": 3,
                    "end_line": 5,
                    "heading": "Deployment",
                    "action": "extend_skill",
                    "scores": {"overall": 0.8},
                    "evidence": ["ordered_steps"],
                }
            ],
            "classifications": [
                {
                    "source_path": "AGENTS.md",
                    "start_line": 1,
                    "end_line": 3,
                    "classification": "global_guardrail",
                    "heading": "Agent Rules",
                }
            ],
            "issues": [],
            "summary": {
                "skill_count": 1,
                "candidate_count": 1,
                "error_count": 0,
                "warning_count": 0,
                "recommendation_count": 0,
            },
        }
        with patch.object(module, "run_skill_audit", return_value=report), patch.object(
            sys, "argv", ["skill-audit", "--project", "synthetic-project"]
        ), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(module.main(), 0)
        self.assertIn("Existing skills: 1", output.getvalue())
        self.assertIn("global_guardrail", output.getvalue())

        with patch.object(module, "run_skill_audit", return_value=report), patch.object(
            sys, "argv", ["skill-audit", "--project", "synthetic-project", "--json"]
        ), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(module.main(), 0)
        self.assertIn('"project": "synthetic-project"', output.getvalue())

    def test_documentation_lint_includes_nonblocking_skill_recommendations(self) -> None:
        oversized_dir = self.project_root / ".agents" / "skills" / "large"
        oversized_dir.mkdir()
        (oversized_dir / "SKILL.md").write_text(
            "---\nname: large\ndescription: Large synthetic skill.\n---\n"
            + "# Large Skill\n"
            + "\n".join(f"Step {line}: verify the workflow." for line in range(301)),
            encoding="utf-8",
        )
        with (
            patch("rag.lint.get_project_config", return_value=self.config),
            patch(
                "rag.lint.documentation_readiness",
                return_value={"items": [], "coverage": {"percent": 100}, "recommendations": []},
            ),
            patch("rag.lint.load_index", side_effect=FileNotFoundError),
            patch("rag.skill_intelligence.log_operation"),
        ):
            from rag.lint import lint_project

            report = lint_project("synthetic-project")

        self.assertFalse(any(item["type"] == "skill_oversized_skill" for item in report["issues"]))
        self.assertEqual(report["statistics"]["skill_recommendations"], 1)
        self.assertEqual(report["statistics"]["skill_count"], 2)
        self.assertIn("Skill architecture:", report["recommendations"][0])

    def test_apply_rejects_project_escape_and_secret_content(self) -> None:
        with patch("rag.skill_intelligence.HUB_ROOT", self.hub_root), patch(
            "rag.skill_intelligence.SKILL_STORAGE_DIR", self.storage
        ), patch("rag.skill_intelligence.log_operation"):
            proposal = create_skill_proposal(
                self.config,
                action="create_skill",
                source_references=[],
                target_paths=[".agents/skills/blocked/SKILL.md"],
                evidence=[],
                confidence=0.5,
                reason="test",
            )
            with self.assertRaises(ValueError):
                create_skill_proposal(
                    self.config,
                    action="create_skill",
                    source_references=[],
                    target_paths=["../outside.md"],
                    evidence=[],
                    confidence=0.5,
                    reason="test",
                )
            with self.assertRaises(PermissionError):
                apply_skill_proposal(
                    self.config,
                    proposal["proposal_id"],
                    files={
                        ".agents/skills/blocked/SKILL.md":
                            "---\nname: blocked\ndescription: test\n---\napi_key=synthetic-secret-value\n"
                    },
                    confirm=True,
                )

    def test_apply_refuses_stale_target_and_symlink_escape(self) -> None:
        with patch("rag.skill_intelligence.HUB_ROOT", self.hub_root), patch(
            "rag.skill_intelligence.SKILL_STORAGE_DIR", self.storage
        ), patch("rag.skill_intelligence.log_operation"):
            skill_path = ".agents/skills/deploy/SKILL.md"
            proposal = create_skill_proposal(
                self.config,
                action="extend_skill",
                source_references=[{"source_path": "docs/workflow.md"}],
                target_paths=[skill_path],
                evidence=["verified_test"],
                confidence=0.9,
                reason="Update the existing workflow.",
            )
            (self.project_root / skill_path).write_text("Changed after proposal creation.\n", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                apply_skill_proposal(
                    self.config,
                    proposal["proposal_id"],
                    files={
                        skill_path:
                            "---\nname: deploy\ndescription: Deploy safely.\n---\n# Deploy\n"
                    },
                    confirm=True,
                )

            outside = self.base / "outside.md"
            outside.write_text("Outside project.\n", encoding="utf-8")
            escaped_path = self.project_root / ".agents" / "skills" / "outside"
            escaped_path.symlink_to(outside)
            with self.assertRaises(ValueError):
                create_skill_proposal(
                    self.config,
                    action="create_skill",
                    source_references=[],
                    target_paths=[".agents/skills/outside/SKILL.md"],
                    evidence=[],
                    confidence=0.5,
                    reason="Reject symlinked target.",
                )

    def test_apply_never_writes_inside_hub_root(self) -> None:
        hub_config = make_project(self.hub_root)
        skill_path = ".agents/skills/hub-write/SKILL.md"
        with (
            patch("rag.skill_intelligence.HUB_ROOT", self.hub_root),
            patch("rag.skill_intelligence.SKILL_STORAGE_DIR", self.storage),
            patch("rag.skill_intelligence.log_operation"),
        ):
            proposal = create_skill_proposal(
                hub_config,
                action="create_skill",
                source_references=[],
                target_paths=[skill_path],
                evidence=[],
                confidence=0.8,
                reason="Test Hub write boundary.",
            )
            with self.assertRaises(PermissionError):
                apply_skill_proposal(
                    hub_config,
                    proposal["proposal_id"],
                    files={
                        skill_path:
                            "---\nname: hub-write\ndescription: Must not be written.\n---\n# Skill\n"
                    },
                    confirm=True,
                )
        self.assertFalse((self.hub_root / skill_path).exists())

    def test_local_artifact_storage_rejects_symlink_escape(self) -> None:
        self.storage.mkdir(parents=True)
        outside_storage = self.base / "outside-storage"
        outside_storage.mkdir()
        (self.storage / "synthetic-project").symlink_to(
            outside_storage,
            target_is_directory=True,
        )
        with (
            patch("rag.skill_intelligence.HUB_ROOT", self.hub_root),
            patch("rag.skill_intelligence.SKILL_STORAGE_DIR", self.storage),
            patch("rag.skill_intelligence.log_operation"),
        ):
            with self.assertRaises(ValueError):
                run_skill_audit(self.config)
        self.assertEqual(list(outside_storage.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
