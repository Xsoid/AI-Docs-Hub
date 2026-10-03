from __future__ import annotations

import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path

from rag.config import load_project_configs
from rag.project_config_editor import (
    ProjectArtifactRefreshError,
    ProjectConfigEditError,
    refresh_project_artifacts,
    save_project_config,
)


class ProjectConfigEditorTests(unittest.TestCase):
    def test_creates_loadable_project_config_with_safe_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            configs_dir = Path(directory)
            root = configs_dir / "project-root"
            root.mkdir()
            config = save_project_config(
                {
                    "project": "new-project",
                    "title": "New Project",
                    "namespace": "new-project",
                    "root": str(root),
                    "docs_backend": "auto",
                    "mkdocs_config": "mkdocs.yml",
                    "include": ["README.md", "docs/**/*.md"],
                    "exclude": [".env", "**/*.key"],
                },
                mode="create",
                configs_dir=configs_dir,
            )
            self.assertEqual(config.title, "New Project")
            self.assertIn(".env", config.exclude)
            self.assertEqual(load_project_configs(configs_dir)["new-project"].root, root.resolve())

    def test_updates_editable_fields_and_preserves_sources_and_rules(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            configs_dir = Path(directory)
            root = configs_dir / "project-root"
            root.mkdir()
            created = save_project_config(
                {
                    "project": "new-project",
                    "title": "Before",
                    "namespace": "new-project",
                    "root": str(root),
                    "docs_backend": "auto",
                    "mkdocs_config": "mkdocs.yml",
                    "include": ["README.md"],
                    "exclude": [".env"],
                },
                mode="create",
                configs_dir=configs_dir,
            )
            updated = save_project_config(
                {
                    "project": "new-project",
                    "title": "After",
                    "namespace": "new-project-docs",
                    "root": str(root),
                    "docs_backend": "standard",
                    "mkdocs_config": "docs/mkdocs.yml",
                    "include": ["README.md", "docs/**/*.md"],
                    "exclude": [".env", "storage/**"],
                },
                mode="update",
                configs_dir=configs_dir,
            )
            self.assertEqual(updated.title, "After")
            self.assertEqual(updated.namespace, "new-project-docs")
            self.assertEqual(updated.sources, created.sources)
            self.assertEqual(updated.agent_rules, created.agent_rules)
            self.assertEqual(load_project_configs(configs_dir)["new-project"].title, "After")

    def test_rejects_unsafe_project_identifier(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ProjectConfigEditError):
                save_project_config(
                    {
                        "project": "../escape",
                        "title": "Escape",
                        "namespace": "escape",
                        "root": "/tmp/escape",
                        "include": ["README.md"],
                        "exclude": [".env"],
                    },
                    mode="create",
                    configs_dir=Path(directory),
                )

    def test_rejects_duplicate_creation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            configs_dir = Path(directory)
            payload = {
                "project": "new-project",
                "title": "New Project",
                "namespace": "new-project",
                "root": "/tmp/new-project",
                "include": ["README.md"],
                "exclude": [".env"],
            }
            save_project_config(payload, mode="create", configs_dir=configs_dir)
            with self.assertRaises(ProjectConfigEditError):
                save_project_config(payload, mode="create", configs_dir=configs_dir)

    def test_refreshes_project_pages_and_llms_after_a_config_change(self) -> None:
        commands: list[list[str]] = []

        def runner(command: list[str], **_: object) -> SimpleNamespace:
            commands.append(command)
            return SimpleNamespace(returncode=0)

        refresh_project_artifacts(runner=runner)
        self.assertEqual([Path(command[-1]).name for command in commands], ["generate-project-pages", "generate-llms"])

    def test_reports_failed_generated_refresh_without_exposing_command_output(self) -> None:
        def runner(_: list[str], **__: object) -> SimpleNamespace:
            return SimpleNamespace(returncode=1)

        with self.assertRaisesRegex(ProjectArtifactRefreshError, "generated documentation refresh failed"):
            refresh_project_artifacts(runner=runner)


if __name__ == "__main__":
    unittest.main()
