from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch

from rag.config import ProjectConfig
from rag.storage_retention import ProjectLocation, find_orphans, keep_newest, remove_orphans


class KeepNewestTest(unittest.TestCase):
    def test_keeps_newest_names_and_ignores_other_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for stamp in ("20260101T000000Z", "20260201T000000Z", "20260301T000000Z"):
                (root / f"{stamp}-abc.json").write_text("{}", encoding="utf-8")
            (root / "notes.txt").write_text("keep", encoding="utf-8")

            removed = keep_newest(root, "*.json", keep=2)

            self.assertEqual([path.name for path in removed], ["20260101T000000Z-abc.json"])
            self.assertEqual(sorted(path.name for path in root.iterdir()), ["20260201T000000Z-abc.json", "20260301T000000Z-abc.json", "notes.txt"])

    def test_missing_directory_is_a_no_op(self) -> None:
        self.assertEqual(keep_newest(Path("/nonexistent/hub-storage"), "*.json", keep=1), [])

    def test_removes_stale_directories_with_their_contents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for age, name in enumerate(("newest", "middle", "oldest")):
                (root / name).mkdir()
                (root / name / "review.json").write_text("{}", encoding="utf-8")
                os.utime(root / name, (1_000_000 - age, 1_000_000 - age))

            removed = keep_newest(root, "*", keep=2)

            self.assertEqual([path.name for path in removed], ["oldest"])
            self.assertEqual(sorted(path.name for path in root.iterdir()), ["middle", "newest"])


class OrphanStorageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.storage = Path(self.tmp.name)
        self.locations = (
            ProjectLocation(self.storage / "decision-engine"),
            ProjectLocation(self.storage / "index", r"(?P<project>.+?)(?:_log\.jsonl|\.json)"),
            ProjectLocation(self.storage / "codebase-memory", r"(?P<project>[^_].*?)\.db(?:-shm|-wal)?"),
        )
        for project in ("kept", "gone"):
            (self.storage / "decision-engine" / project).mkdir(parents=True)
            (self.storage / "decision-engine" / project / "metrics.json").write_text("{}", encoding="utf-8")
            (self.storage / "index").mkdir(exist_ok=True)
            (self.storage / "index" / f"{project}.json").write_text("{}", encoding="utf-8")
            (self.storage / "index" / f"{project}_log.jsonl").write_text("", encoding="utf-8")
            (self.storage / "codebase-memory").mkdir(exist_ok=True)
            for suffix in (".db", ".db-wal"):
                (self.storage / "codebase-memory" / f"{project}{suffix}").write_text("", encoding="utf-8")
        (self.storage / "codebase-memory" / "_config.db").write_text("", encoding="utf-8")
        (self.storage / "codebase-memory" / "logs").mkdir()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_finds_only_entries_of_projects_without_config(self) -> None:
        orphans = find_orphans({"kept"}, self.locations)

        self.assertEqual({item["project"] for item in orphans}, {"gone"})
        self.assertEqual(sorted(item["path"].relative_to(self.storage).as_posix() for item in orphans), [
            "codebase-memory/gone.db", "codebase-memory/gone.db-wal",
            "decision-engine/gone", "index/gone.json", "index/gone_log.jsonl",
        ])
        self.assertTrue(all(item["bytes"] >= 0 for item in orphans))

    def test_remove_deletes_orphans_and_is_idempotent(self) -> None:
        orphans = find_orphans({"kept"}, self.locations)

        remove_orphans(orphans, self.locations)
        remove_orphans(orphans, self.locations)

        self.assertEqual(find_orphans({"kept"}, self.locations), [])
        self.assertTrue((self.storage / "decision-engine" / "kept" / "metrics.json").exists())
        self.assertTrue((self.storage / "codebase-memory" / "_config.db").exists())

    def test_remove_refuses_paths_outside_the_locations(self) -> None:
        outside = Path(self.tmp.name).parent / "not-hub-storage"
        with self.assertRaises(ValueError):
            remove_orphans([{"project": "x", "path": outside, "bytes": 0}], self.locations)


class ContextSnapshotRetentionTest(unittest.TestCase):
    def test_capture_keeps_a_bounded_number_of_snapshots(self) -> None:
        from rag import context_freshness

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            snapshots = Path(tmp) / "snapshots"
            config = ProjectConfig(
                project="retention-project", namespace="retention-project", title="Retention", root=root,
                root_source=str(root), docs_backend="standard", mkdocs_config="mkdocs.yml",
                sources=[], include=[], exclude=[], agent_rules=[], config_path=root / "project.yaml",
                raw={}, schema_version=1,
            )
            identity = {"fingerprint": "f", "components": {}}
            with patch.object(context_freshness, "SNAPSHOT_DIR", snapshots), \
                    patch.object(context_freshness, "MAX_CONTEXT_SNAPSHOTS", 3), \
                    patch.object(context_freshness, "_config", return_value=config), \
                    patch.object(context_freshness, "current_context_identity", return_value=identity):
                ids = [context_freshness.capture_project_context(config)["snapshot_id"] for _ in range(5)]

            kept = sorted(path.stem for path in (snapshots / "retention-project").glob("*.json"))
            self.assertEqual(len(kept), 3)
            self.assertIn(ids[-1], kept)


class OperationLogRetentionTest(unittest.TestCase):
    def test_log_keeps_a_bounded_number_of_newest_entries(self) -> None:
        from rag import logging as operation_log

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(operation_log, "INDEX_DIR", Path(tmp)), patch.object(operation_log, "MAX_OPERATION_LOG_ENTRIES", 3):
                for step in range(5):
                    operation_log.log_operation("retention-project", "step", {"step": step})
                entries = operation_log.read_operation_log("retention-project")

        self.assertEqual([entry["step"] for entry in entries], [4, 3, 2])


def load_apply_fix():
    path = Path(__file__).resolve().parents[1] / "scripts" / "apply-fix"
    loader = SourceFileLoader("apply_fix_under_test", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    if spec is None:
        raise RuntimeError("could not load apply-fix")
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class FixJobRetentionTest(unittest.TestCase):
    def test_new_job_keeps_a_bounded_number_of_job_files(self) -> None:
        apply_fix = load_apply_fix()
        with tempfile.TemporaryDirectory() as tmp:
            fixes = Path(tmp)
            with patch.object(apply_fix, "FIX_DIR", fixes), patch.object(apply_fix, "MAX_FIX_JOBS", 2):
                for index in range(4):
                    apply_fix.write_job(f"job-{index}", {"status": "queued"})
                    os.utime(fixes / f"job-{index}.json", (1_000_000 + index, 1_000_000 + index))
                apply_fix.write_job("job-3", {"status": "ok"})

            self.assertEqual(sorted(path.name for path in fixes.iterdir()), ["job-2.json", "job-3.json"])
            self.assertEqual(json.loads((fixes / "job-3.json").read_text(encoding="utf-8"))["status"], "ok")


class StoragePruneCliTest(unittest.TestCase):
    def run_cli(self, storage: Path, *args: str) -> dict:
        env = {**os.environ, "HUB_STORAGE_DIR": str(storage)}
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run([sys.executable, str(root / "scripts" / "storage-prune"), "--json", *args], cwd=root, env=env, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_dry_run_lists_and_apply_deletes_orphan_storage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            storage = Path(tmp).resolve()
            orphan = storage / "decision-engine" / "zz-removed-project"
            orphan.mkdir(parents=True)
            (orphan / "metrics.json").write_text("{}", encoding="utf-8")

            dry_run = self.run_cli(storage)
            self.assertEqual(dry_run["orphan_projects"], ["zz-removed-project"])
            self.assertEqual(dry_run["removed"], [])
            self.assertTrue(orphan.exists())

            applied = self.run_cli(storage, "--apply")
            self.assertEqual(applied["removed"], ["storage/decision-engine/zz-removed-project"])
            self.assertFalse(orphan.exists())


if __name__ == "__main__":
    unittest.main()
