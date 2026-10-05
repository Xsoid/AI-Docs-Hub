from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rag.config import (
    ProjectConfigSchemaError,
    load_project_configs,
    validate_all_configs,
    validate_project_config,
    validate_project_config_schema,
)


class ProjectConfigSchemaTests(unittest.TestCase):
    def test_valid_v1_config_is_loaded_strictly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            path = Path(directory) / "valid.yaml"
            path.write_text(
                """schema_version: 1
project: valid-project
root: """ + str(root) + """
sources:
  - path: docs
    type: markdown
include:
  - docs/**/*.md
""",
                encoding="utf-8",
            )
            config = load_project_configs(Path(directory))["valid-project"]
            self.assertEqual(config.schema_version, 1)
            self.assertEqual(config.namespace, "valid-project")
            self.assertFalse([issue for issue in validate_project_config(config) if issue["level"] == "error"])

    def test_legacy_config_is_accepted_with_warning(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            path = Path(directory) / "legacy.yaml"
            path.write_text(f"project: legacy\nroot: {root}\ninclude:\n  - README.md\n", encoding="utf-8")
            config = load_project_configs(Path(directory))["legacy"]
            issues = validate_project_config(config)
            self.assertIn("legacy_config", [issue.get("code") for issue in issues])

    def test_unknown_field_has_stable_diagnostic(self) -> None:
        issues = validate_project_config_schema({"project": "p", "root": "r", "inlcude": []})
        self.assertIn(
            {"level": "error", "code": "unknown_field", "field": "inlcude", "message": "Unknown project config field: inlcude"},
            issues,
        )

    def test_missing_required_field_is_rejected(self) -> None:
        issues = validate_project_config_schema({"schema_version": 1, "project": "missing-root"})
        self.assertIn(("required_field", "root"), {(issue["code"], issue["field"]) for issue in issues})

    def test_invalid_types_and_source_shape_are_rejected_before_loading(self) -> None:
        issues = validate_project_config_schema(
            {"schema_version": "1", "project": [], "root": "r", "include": "README.md", "sources": [{"path": "docs"}]}
        )
        codes = {(issue["code"], issue["field"]) for issue in issues}
        self.assertIn(("unsupported_schema_version", "schema_version"), codes)
        self.assertIn(("invalid_type", "project"), codes)
        self.assertIn(("invalid_type", "include"), codes)
        self.assertIn(("required_field", "sources[0].type"), codes)
        with self.assertRaises(ProjectConfigSchemaError):
            with tempfile.TemporaryDirectory() as directory:
                Path(directory, "invalid.yaml").write_text("project: 1\nroot: r\n", encoding="utf-8")
                load_project_configs(Path(directory))

    def test_duplicate_project_and_namespace_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            content = "schema_version: 1\nproject: Same\nnamespace: Shared\nroot: " + str(root) + "\ninclude:\n  - README.md\n"
            Path(directory, "a.yaml").write_text(content, encoding="utf-8")
            Path(directory, "b.yaml").write_text(content.replace("project: Same", "project: same"), encoding="utf-8")
            report = validate_all_configs(Path(directory))
            all_codes = [issue.get("code") for issues in report.values() for issue in issues]
            self.assertIn("duplicate_project", all_codes)
            self.assertIn("duplicate_namespace", all_codes)

    def test_empty_namespace_and_invalid_backend_are_schema_errors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            path = Path(directory) / "invalid.yaml"
            path.write_text(
                f"schema_version: 1\nproject: p\nnamespace: ns\nroot: {root}\ndocs_backend: nope\ninclude:\n  - README.md\n",
                encoding="utf-8",
            )
            data = {
                "schema_version": 1,
                "project": "p",
                "namespace": "   ",
                "root": str(root),
                "docs_backend": "nope",
                "include": ["README.md"],
            }
            codes = {(issue["code"], issue["field"]) for issue in validate_project_config_schema(data)}
            self.assertIn(("invalid_value", "namespace"), codes)
            config = load_project_configs(Path(directory))["p"]
            errors = [issue for issue in validate_project_config(config) if issue["level"] == "error"]
            self.assertEqual({issue.get("code") for issue in errors}, {"invalid_enum"})

    def test_placeholder_and_hardcoded_root_diagnostics_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            configs_dir = Path(directory)
            (configs_dir / "placeholder.yaml").write_text(
                "schema_version: 1\nproject: placeholder\nroot: '${UNRESOLVED_PROJECT_ROOT}'\ninclude:\n  - README.md\n",
                encoding="utf-8",
            )
            (configs_dir / "absolute.yaml").write_text(
                f"schema_version: 1\nproject: absolute\nroot: {configs_dir}\ninclude:\n  - README.md\n",
                encoding="utf-8",
            )
            report = validate_all_configs(configs_dir)
            self.assertIn("unresolved_root", {issue.get("code") for issue in report["placeholder"]})
            self.assertIn("hardcoded_absolute_root", {issue.get("code") for issue in report["absolute"]})

    def test_validation_does_not_create_index_or_read_operation_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            configs_dir = Path(directory)
            root = configs_dir / "project"
            root.mkdir()
            (root / "README.md").write_text("# Project\n", encoding="utf-8")
            (configs_dir / "project.yaml").write_text(
                f"schema_version: 1\nproject: project\nroot: {root}\ninclude:\n  - README.md\n",
                encoding="utf-8",
            )
            report = validate_all_configs(configs_dir)
            self.assertFalse([issue for issues in report.values() for issue in issues if issue["level"] == "error"])
            self.assertFalse(list(root.rglob("*.json")))
            self.assertFalse(list(root.rglob("*.jsonl")))


if __name__ == "__main__":
    unittest.main()
