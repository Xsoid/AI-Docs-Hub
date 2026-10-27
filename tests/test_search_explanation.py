from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from rag.lite import search_decisions, search_index, search_modules


def chunk(source_path: str, heading: str, text: str) -> dict[str, str]:
    return {"project": "demo", "namespace": "demo", "source_path": source_path, "heading": heading, "section": heading, "text": text}


INDEX = {
    "namespace": "demo",
    "chunks": [
        chunk("docs/decisions/adr-001.md", "Cache Invalidation", "We invalidate the cache on deploy."),
        chunk("docs/runtime.md", "Runtime", "The deploy script restarts workers. Кэш очищается вручную."),
        chunk("docs/modules/billing.md", "Billing Module", "Billing sends invoices."),
    ],
}


def search(query: str, **kwargs):
    with patch("rag.lite.load_index", return_value=INDEX):
        return search_index("demo", query, **kwargs)["results"]


class SearchExplanationTest(unittest.TestCase):
    def test_result_lists_normalized_matched_query_terms_in_query_order(self) -> None:
        results = {item["source_path"]: item for item in search("Cache DEPLOY cache missing")}

        self.assertEqual(results["docs/decisions/adr-001.md"]["matched_terms"], ["cache", "deploy"])
        self.assertEqual(results["docs/runtime.md"]["matched_terms"], ["deploy"])

    def test_heading_match_reports_a_matched_term_in_the_heading(self) -> None:
        results = {item["source_path"]: item for item in search("cache deploy")}

        self.assertTrue(results["docs/decisions/adr-001.md"]["heading_match"])
        self.assertFalse(results["docs/runtime.md"]["heading_match"])

    def test_query_coverage_is_the_share_of_distinct_query_terms_found(self) -> None:
        results = {item["source_path"]: item for item in search("cache deploy cache workers")}

        self.assertEqual(results["docs/decisions/adr-001.md"]["query_coverage"], 0.667)
        self.assertEqual(results["docs/runtime.md"]["query_coverage"], 0.667)

    def test_explanation_adds_only_query_terms_to_the_result(self) -> None:
        [result] = search("invoices")

        self.assertEqual(result["matched_terms"], ["invoices"])
        explanation = json.dumps({key: result[key] for key in ("matched_terms", "heading_match", "query_coverage")})
        self.assertNotIn("billing", explanation.lower())
        self.assertLessEqual(len(explanation), len(json.dumps(["invoices"])) + 96)

    def test_decision_and_module_search_carry_the_explanation(self) -> None:
        with patch("rag.lite.load_index", return_value=INDEX):
            decision = search_decisions("demo", "cache")["results"][0]
            module = search_modules("demo", "billing")["results"][0]

        self.assertEqual((decision["matched_terms"], decision["heading_match"]), (["cache"], True))
        self.assertEqual((module["matched_terms"], module["heading_match"]), (["billing"], True))


if __name__ == "__main__":
    unittest.main()
