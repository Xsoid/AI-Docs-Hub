from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATUS_PAGE = ROOT / "docs-site" / "src" / "pages" / "status.astro"


class StatusDashboardTests(unittest.TestCase):
    def test_dynamic_dashboard_styles_are_global(self) -> None:
        source = STATUS_PAGE.read_text(encoding="utf-8")
        self.assertIn("<style is:global>", source)
        self.assertIn("function projectCard", source)
        self.assertIn("function renderSystems", source)

    def test_incomplete_project_has_a_real_repair_action(self) -> None:
        source = STATUS_PAGE.read_text(encoding="utf-8")
        self.assertIn("project.repair", source)
        self.assertIn("Привести в порядок", source)
        self.assertIn("r.status==='indexed'&&!r.stale", source)
        self.assertIn("r.secret_blocked_count", source)


if __name__ == "__main__":
    unittest.main()
