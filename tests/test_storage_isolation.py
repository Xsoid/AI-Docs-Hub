from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROBE = """
import json
from rag import config, context_freshness, decision_engine, mcp_audit, project_lifecycle, skill_intelligence
print(json.dumps({
    "index": str(config.INDEX_DIR),
    "decision_engine": str(decision_engine.STORAGE_DIR),
    "context_snapshots": str(context_freshness.SNAPSHOT_DIR),
    "project_lifecycle": str(project_lifecycle.LIFECYCLE_STORAGE_DIR),
    "skill_intelligence": str(skill_intelligence.SKILL_STORAGE_DIR),
    "mcp_audit": str(mcp_audit.audit_directory()),
}))
"""


def isolated_env(storage: Path) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key != "MCP_AUDIT_DIR"}
    env["HUB_STORAGE_DIR"] = str(storage)
    return env


class StorageIsolationTest(unittest.TestCase):
    def test_storage_override_moves_every_writer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            storage = Path(tmp).resolve()
            result = subprocess.run([sys.executable, "-c", PROBE], cwd=ROOT, env=isolated_env(storage), capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            for name, path in json.loads(result.stdout).items():
                self.assertTrue(Path(path).is_relative_to(storage), f"{name} escapes HUB_STORAGE_DIR: {path}")

    def test_llms_generation_writes_into_storage_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            storage = Path(tmp).resolve()
            result = subprocess.run([sys.executable, str(ROOT / "scripts" / "generate-llms")], cwd=ROOT, env=isolated_env(storage), capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((storage / "generated" / "llms-report.json").is_file())


if __name__ == "__main__":
    unittest.main()
