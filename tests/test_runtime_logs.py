from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from rag.runtime_logs import prune_logs, rotate_stream


class RotateStreamTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.log = Path(self.tmp.name) / "runtime.out.log"
        self.fd = os.open(self.log, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)

    def tearDown(self) -> None:
        os.close(self.fd)
        self.tmp.cleanup()

    def test_oversized_stream_moves_to_archive_and_keeps_writing_to_log_path(self) -> None:
        os.write(self.fd, b"old\n" * 10)
        self.assertTrue(rotate_stream(self.fd, self.log, max_bytes=16, archives=2))
        os.write(self.fd, b"new\n")
        self.assertEqual(self.log.read_bytes(), b"new\n")
        self.assertEqual(Path(f"{self.log}.1").read_bytes(), b"old\n" * 10)

    def test_small_stream_is_not_rotated(self) -> None:
        os.write(self.fd, b"small\n")
        self.assertFalse(rotate_stream(self.fd, self.log, max_bytes=16, archives=2))
        self.assertFalse(Path(f"{self.log}.1").exists())

    def test_stream_of_another_file_is_not_rotated(self) -> None:
        other = Path(self.tmp.name) / "terminal.log"
        other_fd = os.open(other, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            os.write(other_fd, b"x" * 64)
            self.assertFalse(rotate_stream(other_fd, self.log, max_bytes=16, archives=2))
        finally:
            os.close(other_fd)
        self.assertFalse(Path(f"{self.log}.1").exists())

    def test_archive_count_is_bounded(self) -> None:
        for generation in range(4):
            os.write(self.fd, f"gen{generation}\n".encode() * 8)
            self.assertTrue(rotate_stream(self.fd, self.log, max_bytes=16, archives=2))
        archives = sorted(path.name for path in Path(self.tmp.name).iterdir() if path.name != self.log.name)
        self.assertEqual(archives, ["runtime.out.log.1", "runtime.out.log.2"])
        self.assertTrue(Path(f"{self.log}.1").read_bytes().startswith(b"gen3"))
        self.assertTrue(Path(f"{self.log}.2").read_bytes().startswith(b"gen2"))


class PruneLogsTest(unittest.TestCase):
    def test_keeps_newest_job_logs_and_ignores_other_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for stamp in ("20260101T000000Z", "20260201T000000Z", "20260301T000000Z"):
                (root / f"apply-fix-{stamp}-rag.reindex-demo-1.log").write_text("job\n", encoding="utf-8")
            (root / "hub-runtime.out.log").write_text("runtime\n", encoding="utf-8")

            removed = prune_logs(root, "apply-fix-*.log", keep=2)

            self.assertEqual([path.name for path in removed], ["apply-fix-20260101T000000Z-rag.reindex-demo-1.log"])
            self.assertEqual(sorted(path.name for path in root.iterdir()), [
                "apply-fix-20260201T000000Z-rag.reindex-demo-1.log",
                "apply-fix-20260301T000000Z-rag.reindex-demo-1.log",
                "hub-runtime.out.log",
            ])


if __name__ == "__main__":
    unittest.main()
