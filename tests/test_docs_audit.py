from __future__ import annotations

import subprocess
import importlib.machinery
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT = importlib.machinery.SourceFileLoader("audit_docs", str(ROOT / "scripts/audit-docs")).load_module()


class DocumentationAuditTests(unittest.TestCase):
    def test_audit_passes_current_canonical_documentation(self) -> None:
        result = subprocess.run(["python3.11", "scripts/audit-docs", "--strict"], cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_audit_flags_broken_relative_link(self) -> None:
        path = ROOT / "docs/standards/temporary-audit-fixture.md"
        try:
            path.write_text("# Fixture\n\n[Missing](does-not-exist.md)\n", encoding="utf-8")
            report = AUDIT.audit()
            self.assertIn(
                {"code": "broken_internal_link", "path": "docs/standards/temporary-audit-fixture.md", "target": "does-not-exist.md"},
                report["errors"],
            )
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
