from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rag.config import ProjectConfig, validate_project_config_schema
from rag.docs_quality import documentation_readiness


def config_for(root: Path, readiness: dict | None = None) -> ProjectConfig:
    raw = {} if readiness is None else {"documentation_readiness": readiness}
    return ProjectConfig(
        project="quality-project",
        namespace="quality-project",
        title="Quality project",
        root=root,
        root_source=str(root),
        docs_backend="standard",
        mkdocs_config="mkdocs.yml",
        sources=[{"path": "docs", "type": "markdown"}],
        include=["docs/**/*.md"],
        exclude=[],
        agent_rules=[],
        config_path=root / "project.yaml",
        raw=raw,
        schema_version=1,
    )


class DocumentationReadinessProfileTests(unittest.TestCase):
    def test_custom_profile_accepts_existing_canonical_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs" / "architecture").mkdir(parents=True)
            (root / "README.md").write_text("# Project\n", encoding="utf-8")
            (root / "docs" / "README.md").write_text("# Documentation\n", encoding="utf-8")
            (root / "docs" / "architecture" / "overview.md").write_text("# Architecture\n", encoding="utf-8")
            readiness = {
                "items": [
                    {"path": "README.md", "kind": "file", "label": "overview", "category": "core"},
                    {"path": "docs/README.md", "kind": "file", "label": "documentation entrypoint", "category": "core"},
                    {"path": "docs/architecture", "kind": "directory", "label": "architecture", "category": "technical"},
                ]
            }
            result = documentation_readiness(config_for(root, readiness))
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["coverage"]["percent"], 100.0)
            self.assertFalse(result["recommendations"])

    def test_custom_profile_reports_only_declared_missing_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            readiness = {
                "items": [
                    {"path": "docs/existing.md", "kind": "file", "label": "existing", "category": "core"},
                    {"path": "docs/missing.md", "kind": "file", "label": "missing", "category": "technical"},
                ]
            }
            (root / "docs").mkdir()
            (root / "docs" / "existing.md").write_text("# Existing\n", encoding="utf-8")
            result = documentation_readiness(config_for(root, readiness))
            self.assertEqual(result["coverage"]["percent"], 50.0)
            self.assertEqual(result["recommendations"], ["Add `docs/missing.md` for missing"])

    def test_profile_schema_rejects_escape_and_unknown_fields(self) -> None:
        issues = validate_project_config_schema(
            {
                "schema_version": 1,
                "project": "quality-project",
                "root": "${AI_DOCS_PROJECTS_ROOT}/quality-project",
                "documentation_readiness": {
                    "items": [
                        {"path": "../outside.md", "kind": "nope", "label": "outside", "category": "other", "extra": True}
                    ]
                },
            }
        )
        codes = {(issue["code"], issue["field"]) for issue in issues}
        self.assertIn(("invalid_value", "documentation_readiness.items[0].path"), codes)
        self.assertIn(("invalid_enum", "documentation_readiness.items[0].kind"), codes)
        self.assertIn(("invalid_enum", "documentation_readiness.items[0].category"), codes)
        self.assertIn(("unknown_field", "documentation_readiness.items[0].extra"), codes)


if __name__ == "__main__":
    unittest.main()
