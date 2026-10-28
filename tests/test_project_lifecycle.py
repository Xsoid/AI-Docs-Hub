from __future__ import annotations

import subprocess
import tempfile
import unittest
import json
import os
from pathlib import Path
from unittest.mock import patch

from rag.config import ProjectConfig
from rag.project_lifecycle import (
    AGENTS_BEGIN,
    LifecycleError,
    onboard_project,
    patch_fingerprint,
    pre_publish_status,
    quality_profile,
    record_review,
    prepare_patch_review,
    verify_patch,
    main as lifecycle_main,
)


def make_config(root: Path) -> ProjectConfig:
    return ProjectConfig(
        project="synthetic-lifecycle",
        namespace="synthetic-lifecycle",
        title="Synthetic lifecycle",
        root=root,
        root_source="<SYNTHETIC_LIFECYCLE_ROOT>",
        docs_backend="standard",
        mkdocs_config="mkdocs.yml",
        sources=[],
        include=["**/*"],
        exclude=[],
        agent_rules=[],
        config_path=root / "project.yaml",
        raw={},
    )


class ProjectLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name) / "project"
        self.root.mkdir()
        (self.root / "app.py").write_text("print('baseline')\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        subprocess.run(["git", "-C", str(self.root), "config", "user.email", "test@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(self.root), "config", "user.name", "Lifecycle Test"], check=True)
        subprocess.run(["git", "-C", str(self.root), "add", "app.py"], check=True)
        subprocess.run(["git", "-C", str(self.root), "commit", "-qm", "baseline"], check=True)
        self.config = make_config(self.root)
        self.storage = Path(self.temp_dir.name) / "hub-storage"

    def test_onboarding_preserves_custom_agents_and_is_idempotent(self) -> None:
        agents = self.root / "AGENTS.md"
        agents.write_text("# Project rules\n\nNever overwrite this sentence.\n", encoding="utf-8")
        with patch("rag.project_lifecycle.LIFECYCLE_STORAGE_DIR", self.storage):
            first = onboard_project(self.config, write=True)
            content_after_first = agents.read_text(encoding="utf-8")
            second = onboard_project(self.config, write=True)
            content_after_second = agents.read_text(encoding="utf-8")

        self.assertEqual(first["status"], "initialized")
        self.assertTrue(first["restart_required"])
        self.assertIn("Never overwrite this sentence.", content_after_first)
        self.assertIn(AGENTS_BEGIN, content_after_first)
        self.assertFalse(second["managed_block_changed"])
        self.assertFalse(second["restart_required"])
        self.assertEqual(content_after_first, content_after_second)
        self.assertTrue((self.storage / "synthetic-lifecycle" / "init.json").is_file())

    def test_fingerprint_changes_for_working_and_staged_content(self) -> None:
        with patch("rag.project_lifecycle.LIFECYCLE_STORAGE_DIR", self.storage):
            clean = patch_fingerprint(self.config)
            (self.root / "app.py").write_text("print('changed')\n", encoding="utf-8")
            working = patch_fingerprint(self.config)
            self.assertNotEqual(clean["fingerprint"], working["fingerprint"])
            subprocess.run(["git", "-C", str(self.root), "add", "app.py"], check=True)
            staged = patch_fingerprint(self.config, scope="staged")

        self.assertEqual(staged["changed_files"], ["app.py"])
        self.assertNotEqual(working["fingerprint"], staged["fingerprint"])

    def test_range_base_rejects_git_option_injection(self) -> None:
        with patch("rag.project_lifecycle.LIFECYCLE_STORAGE_DIR", self.storage):
            with self.assertRaises(LifecycleError):
                patch_fingerprint(self.config, scope="range", base="--output=/tmp/forbidden")

    def test_verification_reviews_and_stale_gate(self) -> None:
        (self.root / "app.py").write_text("print('changed')\n", encoding="utf-8")
        with patch("rag.project_lifecycle.LIFECYCLE_STORAGE_DIR", self.storage):
            verification = verify_patch(self.config)
            self.assertEqual(verification["status"], "passed")
            fingerprint = verification["fingerprint"]
            record_review(self.config, kind="code", scope="working", base=None, fingerprint=fingerprint, status="passed", findings=[])
            record_review(self.config, kind="security", scope="working", base=None, fingerprint=fingerprint, status="passed", findings=[])
            publishable = pre_publish_status(self.config)
            self.assertEqual(publishable["state"], "PUBLISHABLE")
            (self.root / "app.py").write_text("print('changed again')\n", encoding="utf-8")
            stale = pre_publish_status(self.config)

        self.assertNotEqual(stale["fingerprint"], fingerprint)
        self.assertEqual(stale["state"], "VERIFYING")
        self.assertFalse(stale["publishable"])

    def test_review_retention_keeps_current_fingerprint(self) -> None:
        (self.root / "app.py").write_text("print('changed')\n", encoding="utf-8")
        reviews = self.storage / "synthetic-lifecycle" / "reviews"
        with patch("rag.project_lifecycle.LIFECYCLE_STORAGE_DIR", self.storage), patch("rag.project_lifecycle.MAX_REVIEW_FINGERPRINTS", 2):
            fingerprint = verify_patch(self.config)["fingerprint"]
            os.utime(reviews / fingerprint, (1_000_000, 1_000_000))
            for index in range(3):
                stale = reviews / f"stale-{index}"
                stale.mkdir()
                (stale / "verification.json").write_text("{}", encoding="utf-8")
                os.utime(stale, (2_000_000 + index, 2_000_000 + index))
            record_review(self.config, kind="code", scope="working", base=None, fingerprint=fingerprint, status="passed", findings=[])
            record_review(self.config, kind="security", scope="working", base=None, fingerprint=fingerprint, status="passed", findings=[])
            status = pre_publish_status(self.config)

        self.assertEqual(status["state"], "PUBLISHABLE")
        self.assertEqual(sorted(path.name for path in reviews.iterdir()), sorted([fingerprint, "stale-2"]))

    def test_cli_record_review_requires_current_fingerprint(self) -> None:
        (self.root / "app.py").write_text("print('changed')\n", encoding="utf-8")
        findings = Path(self.temp_dir.name) / "findings.json"
        findings.write_text(json.dumps([{"severity": "low", "path": "app.py", "line": 1, "evidence": "synthetic", "extra": "dropped"}]), encoding="utf-8")
        with patch("rag.project_lifecycle.LIFECYCLE_STORAGE_DIR", self.storage), patch("rag.project_lifecycle.get_project_config", return_value=self.config), patch("builtins.print"):
            fingerprint = verify_patch(self.config)["fingerprint"]
            stale = lifecycle_main(["record-review", "--project", "synthetic-lifecycle", "--kind", "code", "--fingerprint", "0" * 64, "--status", "passed"])
            missing = lifecycle_main(["record-review", "--project", "synthetic-lifecycle", "--kind", "code"])
            recorded = lifecycle_main(["record-review", "--project", "synthetic-lifecycle", "--kind", "code", "--fingerprint", fingerprint, "--status", "passed", "--findings-file", str(findings), "--reviewer", "claude-code"])
            gate = pre_publish_status(self.config)

        self.assertEqual((stale, missing, recorded), (1, 1, 0))
        record = json.loads((self.storage / "synthetic-lifecycle" / "reviews" / fingerprint / "code-review.json").read_text(encoding="utf-8"))
        self.assertEqual(record["reviewer"], "claude-code")
        self.assertNotIn("extra", record["findings"][0])
        self.assertEqual(gate["state"], "SECURITY_REVIEW_REQUIRED")

    def test_secret_path_is_hard_block_and_profile_is_metadata_only(self) -> None:
        (self.root / ".env").write_text("TOKEN=synthetic-secret-value\n", encoding="utf-8")
        with patch("rag.project_lifecycle.LIFECYCLE_STORAGE_DIR", self.storage):
            profile = quality_profile(self.config)
            verification = verify_patch(self.config)

        self.assertEqual(verification["status"], "failed")
        self.assertEqual(profile["project"], "synthetic-lifecycle")
        self.assertNotIn(str(self.root), json_text(profile))
        self.assertFalse((self.storage / "synthetic-lifecycle" / "quality-profile.json").read_text(encoding="utf-8").find(str(self.root)) >= 0)

    def test_declared_public_metadata_path_bypasses_only_name_heuristic(self) -> None:
        metadata = self.root / "docs" / "design" / "tokens.json"
        metadata.parent.mkdir(parents=True)
        metadata.write_text('{"active": "#006C98"}\n', encoding="utf-8")
        config = ProjectConfig(**{**self.config.__dict__, "raw": {"public_metadata_paths": ["docs/design/tokens.json"]}})
        with patch("rag.project_lifecycle.LIFECYCLE_STORAGE_DIR", self.storage):
            verification = verify_patch(config)

        secret = next(check for check in verification["checks"] if check["id"] == "secret-scan")
        self.assertEqual(verification["status"], "passed")
        self.assertEqual(secret["status"], "passed")

    def test_public_metadata_path_does_not_bypass_secret_content_scan(self) -> None:
        metadata = self.root / "docs" / "design" / "tokens.json"
        metadata.parent.mkdir(parents=True)
        metadata.write_text('{"token": "sk-0123456789abcdefghijk"}\n', encoding="utf-8")
        subprocess.run(["git", "-C", str(self.root), "add", str(metadata)], check=True)
        config = ProjectConfig(**{**self.config.__dict__, "raw": {"public_metadata_paths": ["docs/design/tokens.json"]}})
        with patch("rag.project_lifecycle.LIFECYCLE_STORAGE_DIR", self.storage):
            verification = verify_patch(config)

        secret = next(check for check in verification["checks"] if check["id"] == "secret-scan")
        self.assertEqual(verification["status"], "failed")
        self.assertIn("openai_key", {finding["kind"] for finding in secret["findings"]})

    def test_profile_discovers_nested_cargo_and_test_scripts(self) -> None:
        (self.root / "core").mkdir()
        (self.root / "core" / "Cargo.toml").write_text("[package]\nname = \"core\"\n", encoding="utf-8")
        (self.root / "target").mkdir()
        (self.root / "target" / "Cargo.toml").write_text("", encoding="utf-8")
        (self.root / "scripts").mkdir()
        (self.root / "scripts" / "test-core.sh").write_text("exit 0\n", encoding="utf-8")
        (self.root / "scripts" / "build.sh").write_text("exit 0\n", encoding="utf-8")
        with patch("rag.project_lifecycle.LIFECYCLE_STORAGE_DIR", self.storage):
            profile = quality_profile(self.config)

        commands = {item["id"]: (item["command"], item["required"]) for item in profile["verification"]["checks"]}
        self.assertEqual(commands["tests:core"], (["cargo", "test", "--manifest-path", "core/Cargo.toml"], True))
        self.assertEqual(commands["script:test-core"], (["bash", "scripts/test-core.sh"], True))
        self.assertNotIn("tests:target", commands)
        self.assertNotIn("script:build", commands)
        self.assertIn("core/Cargo.toml", profile["manifests"])

    def test_test_script_failure_blocks_verification(self) -> None:
        (self.root / "scripts").mkdir()
        (self.root / "scripts" / "test-fail.sh").write_text("exit 3\n", encoding="utf-8")
        with patch("rag.project_lifecycle.LIFECYCLE_STORAGE_DIR", self.storage):
            verification = verify_patch(self.config)

        check = next(item for item in verification["checks"] if item["id"] == "script:test-fail")
        self.assertEqual((check["status"], check["returncode"]), ("failed", 3))
        self.assertEqual(verification["status"], "failed")

    def test_design_token_file_passes_name_check_only_with_clean_content(self) -> None:
        skill = self.root / ".agents" / "skills" / "design-system"
        (skill / "scripts").mkdir(parents=True)
        (skill / "scripts" / "validate-tokens.cjs").write_text("const color = '#006C98';\n", encoding="utf-8")
        (skill / "primitive-tokens.md").write_text("token: sk-0123456789abcdefghijk\n", encoding="utf-8")
        (self.root / "oauth-token.json").write_text("{}\n", encoding="utf-8")
        with patch("rag.project_lifecycle.LIFECYCLE_STORAGE_DIR", self.storage):
            verification = verify_patch(self.config)

        secret = next(check for check in verification["checks"] if check["id"] == "secret-scan")
        found = {(finding["kind"], finding.get("path")) for finding in secret["findings"]}
        self.assertEqual(verification["status"], "failed")
        self.assertNotIn(("secret_looking_path", ".agents/skills/design-system/scripts/validate-tokens.cjs"), found)
        self.assertIn(("openai_key", ".agents/skills/design-system/primitive-tokens.md"), found)
        self.assertIn(("secret_looking_path", "oauth-token.json"), found)

    def test_adaptive_review_context_distinguishes_docs_and_auth_surface(self) -> None:
        docs_dir = self.root / "docs"
        docs_dir.mkdir()
        (docs_dir / "change.md").write_text("Safe documentation change.\n", encoding="utf-8")
        with patch("rag.project_lifecycle.LIFECYCLE_STORAGE_DIR", self.storage):
            docs_review = prepare_patch_review(self.config, kind="security")
            self.assertEqual(docs_review["security_scope"]["risk_level"], "low")
            self.assertEqual(docs_review["context_budget"]["max_snippet_chars"], 0)
            (self.root / "app.py").write_text("def authorize(user):\n    return True\n", encoding="utf-8")
            auth_review = prepare_patch_review(self.config, kind="security")

        self.assertEqual(auth_review["security_scope"]["risk_level"], "high")
        self.assertIn("authentication", auth_review["security_scope"]["surface"])

    def test_tampered_verification_and_blocking_security_finding_do_not_publish(self) -> None:
        (self.root / "app.py").write_text("print('changed')\n", encoding="utf-8")
        with patch("rag.project_lifecycle.LIFECYCLE_STORAGE_DIR", self.storage):
            verification = verify_patch(self.config)
            fingerprint = verification["fingerprint"]
            verification_path = self.storage / "synthetic-lifecycle" / "reviews" / fingerprint / "verification.json"
            tampered = json.loads(verification_path.read_text(encoding="utf-8"))
            tampered["scope"] = "staged"
            verification_path.write_text(json.dumps(tampered), encoding="utf-8")
            self.assertEqual(pre_publish_status(self.config)["state"], "VERIFYING")

            verify_patch(self.config)
            record_review(self.config, kind="code", scope="working", base=None, fingerprint=fingerprint, status="passed", findings=[])
            record_review(
                self.config,
                kind="security",
                scope="working",
                base=None,
                fingerprint=fingerprint,
                status="failed",
                findings=[
                    {
                        "severity": "high",
                        "confidence": "high",
                        "path": "app.py",
                        "line": 1,
                        "evidence": "synthetic authz bypass",
                        "impact": "privilege escalation",
                        "remediation": "enforce the project authorization policy",
                    }
                ],
            )
            self.assertEqual(pre_publish_status(self.config)["state"], "SECURITY_REVIEW_FAILED")

    def test_review_eval_catalogs_cover_safe_and_targeted_cases(self) -> None:
        hub_root = Path(__file__).resolve().parents[1]
        code_catalog = json.loads((hub_root / ".agents/skills/code-review/evals/catalog.json").read_text(encoding="utf-8"))
        security_catalog = json.loads((hub_root / ".agents/skills/security-review/evals/catalog.json").read_text(encoding="utf-8"))
        self.assertEqual({item["id"] for item in code_catalog}, {"docs-only-safe", "api-compatibility-regression"})
        self.assertEqual(
            {item["id"] for item in security_catalog},
            {"docs-only-safe", "authz-bypass", "path-traversal", "secret-logging", "dependency-tool-unavailable"},
        )
        self.assertTrue(all(item.get("expected") for item in code_catalog + security_catalog))


def json_text(value: object) -> str:
    import json

    return json.dumps(value, ensure_ascii=False)


if __name__ == "__main__":
    unittest.main()
