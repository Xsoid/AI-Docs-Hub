from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from rag.config import ProjectConfig
from rag.context_freshness import (
    capture_project_context,
    check_project_context,
    current_context_identity,
)


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return result.stdout.strip()


def make_project(root: Path, project: str = "freshness-project") -> ProjectConfig:
    return ProjectConfig(
        project=project,
        namespace=project,
        title="Freshness Project",
        root=root,
        root_source="${AI_DOCS_PROJECTS_ROOT}/freshness-project",
        docs_backend="standard",
        mkdocs_config="mkdocs.yml",
        sources=[{"path": "README.md", "type": "markdown"}],
        include=["README.md"],
        exclude=[".git/**", "node_modules/**", "storage/**", "tmp/**"],
        agent_rules=["Use the project namespace."],
        config_path=root / "project.yaml",
        raw={"exclude": [".git/**", "node_modules/**", "storage/**", "tmp/**"]},
        schema_version=1,
    )


class ContextFreshnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name) / "project"
        self.root.mkdir()
        (self.root / "README.md").write_text("# Initial\n", encoding="utf-8")
        (self.root / "AGENTS.md").write_text("Initial instructions\n", encoding="utf-8")
        git(self.root, "init", "-q")
        git(self.root, "config", "user.email", "tests@example.invalid")
        git(self.root, "config", "user.name", "Freshness Tests")
        git(self.root, "add", "README.md", "AGENTS.md")
        git(self.root, "commit", "-qm", "initial")
        self.config = make_project(self.root)
        self.snapshot_dir = Path(self.directory.name) / "snapshots"
        self.index_dir = Path(self.directory.name) / "index"
        self.snapshot_dir.mkdir()
        self.index_dir.mkdir()

    def tearDown(self) -> None:
        self.directory.cleanup()

    def _identity(self):
        with patch.dict("os.environ", {"CODEBASE_MEMORY_BIN": str(self.root / "missing-codebase-memory")}, clear=False), patch("rag.config.INDEX_DIR", self.index_dir), patch("rag.context_freshness._codebase_identity", return_value={"status": "available", "fingerprint": "stable-codebase", "metadata": {}}):
            return current_context_identity(self.config)

    def _capture(self):
        with patch.dict("os.environ", {"CODEBASE_MEMORY_BIN": str(self.root / "missing-codebase-memory")}, clear=False), patch("rag.config.INDEX_DIR", self.index_dir), patch("rag.context_freshness.SNAPSHOT_DIR", self.snapshot_dir), patch("rag.context_freshness._codebase_identity", return_value={"status": "available", "fingerprint": "stable-codebase", "metadata": {}}):
            return capture_project_context(self.config)

    def _check(self, snapshot_id: str):
        with patch.dict("os.environ", {"CODEBASE_MEMORY_BIN": str(self.root / "missing-codebase-memory")}, clear=False), patch("rag.config.INDEX_DIR", self.index_dir), patch("rag.context_freshness.SNAPSHOT_DIR", self.snapshot_dir), patch("rag.context_freshness._codebase_identity", return_value={"status": "available", "fingerprint": "stable-codebase", "metadata": {}}):
            return check_project_context(self.config, snapshot_id)

    def test_two_unchanged_identities_are_equal_and_snapshot_is_metadata_only(self) -> None:
        (self.index_dir / f"{self.config.project}.json").write_text(json.dumps({
            "schema_version": 1,
            "backend": "lite-json-bm25",
            "project": self.config.project,
            "namespace": self.config.namespace,
            "source_plan": {"include": ["README.md"]},
            "documents": [],
        }), encoding="utf-8")
        first = self._identity()
        second = self._identity()
        self.assertEqual(first["fingerprint"], second["fingerprint"])
        snapshot = self._capture()
        raw = json.dumps(snapshot, ensure_ascii=False)
        self.assertNotIn("Initial instructions", raw)
        self.assertNotIn("# Initial", raw)
        self.assertEqual(self._check(snapshot["snapshot_id"])["state"], "fresh")

    def test_head_and_dirty_patch_changes_are_stale_git(self) -> None:
        snapshot = self._capture()
        (self.root / "README.md").write_text("# Dirty\n", encoding="utf-8")
        self.assertIn("git", self._check(snapshot["snapshot_id"])["changed_components"])
        git(self.root, "add", "README.md")
        git(self.root, "commit", "-qm", "changed")
        self.assertIn("git", self._check(snapshot["snapshot_id"])["changed_components"])

    def test_config_instruction_and_skill_changes_are_component_stale(self) -> None:
        snapshot = self._capture()
        changed_config = replace(make_project(self.root), include=["README.md", "docs/**/*.md"])
        with patch("rag.config.INDEX_DIR", self.index_dir), patch("rag.context_freshness.SNAPSHOT_DIR", self.snapshot_dir), patch("rag.context_freshness._codebase_identity", return_value={"status": "available", "fingerprint": "stable-codebase", "metadata": {}}):
            result = check_project_context(changed_config, snapshot["snapshot_id"])
        self.assertIn("config", result["changed_components"])

        (self.root / "AGENTS.md").write_text("Changed instructions\n", encoding="utf-8")
        self.assertIn("instructions", self._check(snapshot["snapshot_id"])["changed_components"])

        skill = self.root / ".agents" / "skills" / "ui"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("---\nname: ui\n---\nInitial\n", encoding="utf-8")
        self.assertIn("skills", self._check(snapshot["snapshot_id"])["changed_components"])

    def test_docs_timestamp_does_not_stale_but_document_hash_does(self) -> None:
        index = {
            "schema_version": 1,
            "backend": "lite-json-bm25",
            "project": self.config.project,
            "namespace": self.config.namespace,
            "source_plan": {"include": ["README.md"]},
            "indexed_at": "first",
            "documents_count": 1,
            "chunks_count": 1,
            "documents": [{"source_path": "README.md", "content_hash": "same"}],
        }
        index_path = self.index_dir / f"{self.config.project}.json"
        index_path.write_text(json.dumps(index), encoding="utf-8")
        snapshot = self._capture()
        index["indexed_at"] = "second"
        index_path.write_text(json.dumps(index), encoding="utf-8")
        self.assertEqual(self._check(snapshot["snapshot_id"])["state"], "fresh")
        index["documents"][0]["content_hash"] = "changed"
        index_path.write_text(json.dumps(index), encoding="utf-8")
        self.assertIn("docs_index", self._check(snapshot["snapshot_id"])["changed_components"])

    def test_unavailable_codebase_is_degraded_not_crash(self) -> None:
        with patch.dict("os.environ", {"CODEBASE_MEMORY_BIN": str(self.root / "missing-codebase-memory")}, clear=False), patch("rag.config.INDEX_DIR", self.index_dir), patch("rag.context_freshness.SNAPSHOT_DIR", self.snapshot_dir):
            snapshot = capture_project_context(self.config)
            result = check_project_context(self.config, snapshot["snapshot_id"])
        self.assertEqual(result["state"], "degraded")
        self.assertIn("codebase_index", result["unknown_components"])

    def test_snapshot_id_and_project_isolation(self) -> None:
        snapshot = self._capture()
        with self.assertRaises(ValueError):
            self._check("../escape")
        other = make_project(self.root, project="other-project")
        with patch("rag.context_freshness.SNAPSHOT_DIR", self.snapshot_dir):
            result = check_project_context(other, snapshot["snapshot_id"])
        self.assertEqual(result["state"], "missing")


if __name__ == "__main__":
    unittest.main()
