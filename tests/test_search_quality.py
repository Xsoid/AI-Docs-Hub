from __future__ import annotations

import unittest
from unittest.mock import patch

from mcp.server import McpServer
from rag.lite import search_decisions, search_index, search_modules, source_weight
from tests.search_eval import build_fixture_index, evaluate, run_query


# Ranking before this evaluation set existed: MRR 0.717, recall@5 0.8, 12 duplicate paths.
BASELINE_MRR = 0.717
BASELINE_RECALL_AT_5 = 0.8


class SearchQualityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = build_fixture_index()
        cls.report = evaluate()

    def top_path(self, query: str) -> str:
        return run_query(self.index, query)[0]["source_path"]

    def test_evaluation_set_beats_baseline(self) -> None:
        self.assertGreater(self.report["mrr"], BASELINE_MRR)
        self.assertGreaterEqual(self.report["recall_at_5"], BASELINE_RECALL_AT_5)

    def test_results_do_not_repeat_a_source_file(self) -> None:
        self.assertEqual(self.report["duplicates"], 0)

    def test_one_long_source_file_does_not_bury_the_document(self) -> None:
        self.assertEqual(self.top_path("worker concurrency"), "docs/architecture/queue.md")

    def test_tests_and_scripts_rank_below_decisions_and_architecture(self) -> None:
        self.assertIn(self.top_path("cache invalidation"), {"docs/decisions/adr-002-cache-invalidation.md", "docs/architecture/cache.md"})

    def test_change_notes_rank_below_operations_docs(self) -> None:
        self.assertEqual(self.top_path("deploy rollback"), "docs/operations/deploy.md")

    def test_equal_scores_break_ties_by_path(self) -> None:
        index = {"namespace": "demo", "chunks": [
            {"source_path": path, "heading": "Notes", "section": "Notes", "text": "alpha beta"}
            for path in ("docs/b.md", "docs/c.md", "docs/a.md")
        ]}
        with patch("rag.lite.load_index", return_value=index):
            paths = [item["source_path"] for item in search_index("demo", "alpha")["results"]]
        self.assertEqual(paths, ["docs/a.md", "docs/b.md", "docs/c.md"])


class SourceWeightTest(unittest.TestCase):
    def test_low_priority_sources(self) -> None:
        for path in ("tests/test_cache.py", "app/CacheTests.swift", "scripts/test-cache.sh", "CHANGELOG.md", "docs/changes/2026-01-10-fix.md", "src/cache_test.go"):
            self.assertLess(source_weight(path), 1.0, path)

    def test_high_priority_sources(self) -> None:
        for path in ("docs/decisions/adr-002.md", "docs/adr/0001-queue.md", "docs/architecture/cache.md", "AGENTS.md", "app/CLAUDE.md", "README.md"):
            self.assertGreater(source_weight(path), 1.0, path)

    def test_other_sources_are_neutral(self) -> None:
        for path in ("docs/operations/deploy.md", "src/worker.py", "docs/guide.md"):
            self.assertEqual(source_weight(path), 1.0, path)


class MinConfidenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = build_fixture_index()

    def search(self, function, query: str, **kwargs):
        with patch("rag.lite.load_index", return_value=self.index):
            return function("search-eval", query, **kwargs)["results"]

    def test_default_keeps_every_result(self) -> None:
        self.assertEqual(len(self.search(search_index, "queue retry policy")), len(self.search(search_index, "queue retry policy", min_confidence=0.0)))

    def test_threshold_drops_weaker_results_in_every_search_tool(self) -> None:
        results = self.search(search_index, "queue retry policy")
        threshold = results[0]["confidence"]
        strong = self.search(search_index, "queue retry policy", min_confidence=threshold)
        self.assertTrue(strong)
        self.assertLess(len(strong), len(results))
        self.assertTrue(all(item["confidence"] >= threshold for item in strong))
        self.assertEqual(self.search(search_decisions, "cache invalidation", min_confidence=0.99), [])
        self.assertEqual(self.search(search_modules, "billing", min_confidence=0.99), [])

    def test_mcp_rejects_out_of_range_threshold(self) -> None:
        server = McpServer(active_project="search-eval")
        with patch("mcp.server.get_project_config"):
            response = server.handle_request({"id": 1, "method": "tools/call", "params": {
                "name": "search_docs", "arguments": {"query": "cache", "min_confidence": 1.5}}})
        self.assertTrue(response["result"]["isError"])
        self.assertIn("min_confidence", response["result"]["content"][0]["text"])


if __name__ == "__main__":
    unittest.main()
