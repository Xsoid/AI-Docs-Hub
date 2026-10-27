"""Synthetic search evaluation set: build an in-memory index from the fixture and score rankings."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

from rag.lite import chunk_document, search_index


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "search-eval"
TOP_K = 8
RECALL_AT = 5


def load_queries() -> list[dict[str, Any]]:
    return json.loads((FIXTURE / "queries.json").read_text(encoding="utf-8"))


def build_fixture_index() -> dict[str, Any]:
    root = FIXTURE / "project"
    chunks = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        rel = path.relative_to(root).as_posix()
        for chunk in chunk_document(rel, path.read_text(encoding="utf-8")):
            chunks.append({"project": "search-eval", "namespace": "search-eval", "source_path": rel, **chunk})
    return {"namespace": "search-eval", "chunks": chunks}


def run_query(index: dict[str, Any], query: str) -> list[dict[str, Any]]:
    with patch("rag.lite.load_index", return_value=index):
        return search_index("search-eval", query, limit=TOP_K)["results"]


def evaluate() -> dict[str, Any]:
    """Return MRR and recall@5 over distinct source paths, plus duplicate paths in the top results."""
    index = build_fixture_index()
    per_query = []
    for case in load_queries():
        paths = [item["source_path"] for item in run_query(index, case["query"])]
        relevant = set(case["relevant"])
        rank = next((position for position, path in enumerate(paths, start=1) if path in relevant), None)
        found = relevant.intersection(paths[:RECALL_AT])
        per_query.append({
            "query": case["query"],
            "reciprocal_rank": 1 / rank if rank else 0.0,
            "recall": len(found) / len(relevant),
            "duplicates": len(paths) - len(set(paths)),
            "top": paths[:RECALL_AT],
        })
    count = len(per_query)
    return {
        "mrr": round(sum(item["reciprocal_rank"] for item in per_query) / count, 3),
        "recall_at_5": round(sum(item["recall"] for item in per_query) / count, 3),
        "duplicates": sum(item["duplicates"] for item in per_query),
        "queries": per_query,
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), ensure_ascii=False, indent=2))
