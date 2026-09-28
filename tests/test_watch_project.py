from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch

from rag.config import ProjectConfig


def load_watcher():
    path = Path(__file__).resolve().parents[1] / "scripts" / "watch-project"
    name = "watch_project_for_tests"
    loader = SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    if spec is None:
        raise RuntimeError("could not load watch-project")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


class WatchProjectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.watcher = load_watcher()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        root = Path(self.temp_dir.name)
        (root / "docs").mkdir()
        (root / "docs" / "one.md").write_text("one\n", encoding="utf-8")
        (root / ".agents" / "skills" / "demo").mkdir(parents=True)
        (root / ".agents" / "skills" / "demo" / "SKILL.md").write_text(
            "---\nname: demo\ndescription: Demo skill.\n---\n",
            encoding="utf-8",
        )
        self.config = ProjectConfig(
            project="synthetic-project",
            namespace="synthetic-project",
            title="Synthetic Project",
            root=root,
            root_source=str(root),
            docs_backend="standard",
            mkdocs_config="mkdocs.yml",
            sources=[],
            include=["docs/**/*.md"],
            exclude=[],
            agent_rules=[],
            config_path=root / "project.yaml",
            raw={},
        )

    def test_snapshot_includes_skill_intelligence_sources(self) -> None:
        snapshot = self.watcher.snapshot_project(self.config)

        self.assertIn("docs/one.md", snapshot)
        self.assertIn(".agents/skills/demo/SKILL.md", snapshot)

    def test_refresh_runs_skill_audit_after_reindex(self) -> None:
        report = {"status": "ok", "summary": {"skill_count": 3, "candidate_count": 0}}
        with patch.object(self.watcher, "reindex", return_value=True) as reindex, patch.object(
            self.watcher, "run_skill_audit", return_value=report
        ) as audit:
            self.assertTrue(self.watcher.refresh_project(self.config, generate_llms=False))

        reindex.assert_called_once_with(self.config, generate_llms=False)
        audit.assert_called_once_with(self.config)

    def test_refresh_can_explicitly_disable_skill_audit(self) -> None:
        with patch.object(self.watcher, "reindex", return_value=True), patch.object(
            self.watcher, "run_skill_audit"
        ) as audit:
            self.assertTrue(
                self.watcher.refresh_project(
                    self.config,
                    generate_llms=False,
                    skill_audit=False,
                )
            )

        audit.assert_not_called()

    def test_failed_refresh_snapshot_is_retried_after_delay(self) -> None:
        state = self.watcher.WatchState(snapshot={"docs/one.md": (1, 1)})
        key = self.watcher.snapshot_key(state.snapshot)
        state.last_attempted_snapshot_key = key
        state.retry_after = 10.0

        self.assertFalse(self.watcher.can_attempt_snapshot(state, key, 9.0))
        self.assertTrue(self.watcher.can_attempt_snapshot(state, key, 10.0))


if __name__ == "__main__":
    unittest.main()
