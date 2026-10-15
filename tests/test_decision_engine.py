from __future__ import annotations

import json
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from rag.config import ProjectConfig
from rag.decision_engine import DecisionEngine, EngineSettings


def config(root: Path, project: str = "synthetic") -> ProjectConfig:
    return ProjectConfig(project, project, project, root, "<SYNTHETIC>", "standard", "mkdocs.yml", [], ["**/*"], [], [], root / "project.yaml", {})


class DecisionEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.engine = DecisionEngine(config(self.root), storage_dir=self.root / "storage")

    def request(self, decision_id: str, features: dict[str, object], **extra: object) -> dict[str, object]:
        return {"version": 1, "project": "synthetic", "namespace": "synthetic", "decision_id": decision_id, "features": features, "fingerprint": "a" * 64, **extra}

    def test_strict_types_and_choice_and_score_bounds(self) -> None:
        boolean_as_number = self.engine.evaluate(self.request("patch.security_review_depth", {"risk_level": "low", "has_security_surface": 1, "docs_only": False}))
        invalid_choice = self.engine.evaluate(self.request("patch.risk", {"risk_level": "critical", "surface_count": 0, "changed_files_count": 1}))
        invalid_score = self.engine.evaluate(self.request("skill.candidate_priority", {"candidate_score": 2, "validation_errors": 0}))
        self.assertEqual(boolean_as_number["status"], "unsupported")
        self.assertEqual(invalid_choice["status"], "unsupported")
        self.assertEqual(invalid_score["status"], "unsupported")

    def test_shadow_is_explicitly_non_impacting_and_disabled_abstains(self) -> None:
        result = self.engine.evaluate(self.request("patch.risk", {"risk_level": "low", "surface_count": 0, "changed_files_count": 1}))
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["actual_mode"], "shadow")
        self.assertTrue(result["escalation_required"])
        disabled = DecisionEngine(config(self.root), EngineSettings(enabled=False), self.root / "storage").evaluate(self.request("patch.risk", {"risk_level": "low", "surface_count": 0, "changed_files_count": 1}))
        self.assertEqual(disabled["status"], "unavailable")
        self.assertIsNone(disabled["value"])

    def test_fingerprint_and_project_are_cache_isolated(self) -> None:
        request = self.request("patch.risk", {"risk_level": "medium", "surface_count": 1, "changed_files_count": 1})
        first = self.engine.evaluate(request)
        second = self.engine.evaluate(request)
        stale = self.engine.evaluate({**request, "fingerprint": "b" * 64})
        other = DecisionEngine(config(self.root, "other"), storage_dir=self.root / "storage").evaluate({**request, "project": "other", "namespace": "other"})
        self.assertEqual(first["cache"], "miss")
        self.assertEqual(second["cache"], "hit")
        self.assertEqual(stale["cache"], "miss")
        self.assertEqual(other["cache"], "miss")
        self.assertTrue((self.root / "storage" / "synthetic" / "cache").is_dir())
        self.assertFalse((self.root / "storage" / "other" / "cache").samefile(self.root / "storage" / "synthetic" / "cache"))

    def test_auto_is_not_available_and_uncalibrated_scores_are_not_confidence(self) -> None:
        auto = self.engine.evaluate(self.request("patch.risk", {"risk_level": "low", "surface_count": 0, "changed_files_count": 1}, mode="auto"))
        score = self.engine.evaluate(self.request("patch.risk", {"risk_level": "low", "surface_count": 0, "changed_files_count": 1}, mode="advisory"))
        self.assertEqual(auto["status"], "unsupported")
        self.assertEqual(score["confidence_kind"], "uncalibrated")
        self.assertIsNone(score["confidence"])

    def test_boolean_contract_is_typed(self) -> None:
        result = self.engine.evaluate(self.request("context.docs_ready", {"docs_ready": True}))
        self.assertEqual(result["status"], "ok")
        self.assertIs(result["value"], True)

    def test_stale_patch_fingerprint_escalates(self) -> None:
        (self.root / "file.txt").write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        subprocess.run(["git", "-C", str(self.root), "config", "user.email", "test@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(self.root), "config", "user.name", "Decision Test"], check=True)
        subprocess.run(["git", "-C", str(self.root), "add", "file.txt"], check=True)
        subprocess.run(["git", "-C", str(self.root), "commit", "-qm", "base"], check=True)
        result = self.engine.evaluate(self.request("patch.risk", {"risk_level": "low", "surface_count": 0, "changed_files_count": 1}, scope="working"))
        self.assertEqual(result["status"], "stale")
        self.assertTrue(result["escalation_required"])

    def test_local_provider_blocks_external_and_validates_output(self) -> None:
        external = DecisionEngine(config(self.root), EngineSettings(provider="local", local_endpoint="http://example.com/"), self.root / "storage")
        blocked = external.evaluate(self.request("patch.risk", {"risk_level": "low", "surface_count": 0, "changed_files_count": 1}))
        self.assertEqual(blocked["status"], "unavailable")
        self.assertIn("local_endpoint_not_loopback", blocked["reason_codes"])

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802
                value = 200 if "invalid=1" in self.path else 20
                self.send_response(200); self.end_headers(); self.wfile.write(json.dumps({"status": "ok", "value": value}).encode())
            def log_message(self, format: str, *args: object) -> None: pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        local = DecisionEngine(config(self.root), EngineSettings(provider="local", local_endpoint=f"http://127.0.0.1:{server.server_port}/"), self.root / "other-storage")
        valid = local.evaluate(self.request("patch.risk", {"risk_level": "low", "surface_count": 0, "changed_files_count": 1}))
        self.assertEqual(valid["status"], "ok")
        invalid = DecisionEngine(config(self.root), EngineSettings(provider="local", local_endpoint=f"http://127.0.0.1:{server.server_port}/?invalid=1"), self.root / "invalid-storage").evaluate(self.request("patch.risk", {"risk_level": "low", "surface_count": 0, "changed_files_count": 1}))
        self.assertEqual(invalid["status"], "invalid_output")
