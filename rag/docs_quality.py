from __future__ import annotations

from pathlib import Path
from typing import Any

from .sources import build_source_plan


RECOMMENDED_DIRS = [
    ("architecture", "architecture documentation", "core"),
    ("modules", "module documentation", "core"),
    ("decisions", "architecture decision records", "core"),
    ("api", "API documentation", "core"),
    ("deployment", "deployment documentation", "core"),
    ("operations", "operational runbooks", "technical"),
    ("infrastructure", "infrastructure documentation", "technical"),
]

RECOMMENDED_FILES = [
    ("glossary.md", "project glossary", "core"),
    ("configuration.md", "configuration documentation", "technical"),
    ("security.md", "security documentation", "technical"),
    ("data.md", "data model and storage documentation", "technical"),
    ("integrations.md", "external integrations documentation", "technical"),
    ("observability.md", "observability documentation", "technical"),
    ("testing.md", "testing strategy documentation", "technical"),
    ("troubleshooting.md", "troubleshooting documentation", "technical"),
    ("development.md", "local development documentation", "technical"),
]


def documentation_readiness(config: Any) -> dict[str, Any]:
    root = getattr(config, "root", None)
    if not isinstance(root, Path) or not root.exists() or not root.is_dir():
        return {
            "project": getattr(config, "project", ""),
            "status": "unknown",
            "docs_dir": "docs",
            "items": [],
            "recommendations": [],
            "coverage": {"ok": 0, "total": 0, "percent": 0},
        }

    plan = build_source_plan(config)
    docs_dir = _preferred_docs_dir(config, plan)
    items: list[dict[str, Any]] = []
    recommendations: list[str] = []

    if plan.mkdocs.requested and not plan.mkdocs.detected:
        recommendations.append(
            "Add mkdocs.yml with site_name/docs_dir/nav or switch docs_backend to standard"
        )

    _check_file(root, "README.md", "project overview", items, recommendations)
    _check_file(root, "AGENTS.md", "project-specific agent rules", items, recommendations)

    docs_root = root / docs_dir if docs_dir else root
    if not docs_root.exists() or not docs_root.is_dir():
        items.append(
            {
                "path": docs_dir or ".",
                "kind": "directory",
                "category": "core",
                "status": "missing",
                "message": f"Missing documentation directory: {docs_dir or '.'}",
            }
        )
        recommendations.append(f"Create `{docs_dir or '.'}` and add project documentation")
    else:
        items.append(
            {
                "path": docs_dir or ".",
                "kind": "directory",
                "category": "core",
                "status": "ok",
                "message": f"Documentation directory exists: {docs_dir or '.'}",
            }
        )
        if not any(docs_root.rglob("*.md")):
            items.append(
                {
                    "path": docs_dir or ".",
                    "kind": "content",
                    "category": "core",
                    "status": "empty",
                    "message": f"No Markdown files found under {docs_dir or '.'}",
                }
            )
            recommendations.append(f"Add Markdown documentation under `{docs_dir or '.'}`")

    _check_file(root, _join_rel(docs_dir, "index.md"), "documentation landing page", items, recommendations)

    for child, label, category in RECOMMENDED_DIRS:
        _check_markdown_dir(root, _join_rel(docs_dir, child), label, items, recommendations)
        items[-1]["category"] = category

    for child, label, category in RECOMMENDED_FILES:
        _check_file(root, _join_rel(docs_dir, child), label, items, recommendations)
        items[-1]["category"] = category

    coverage = _coverage(items)
    status = "ok" if not recommendations else "needs_work"
    return {
        "project": getattr(config, "project", ""),
        "status": status,
        "docs_dir": docs_dir or ".",
        "items": items,
        "recommendations": recommendations,
        "coverage": coverage,
        "mkdocs": plan.mkdocs.to_dict(),
    }


def documentation_recommendation_issues(config: Any) -> list[dict[str, str]]:
    readiness = documentation_readiness(config)
    return [
        {"level": "recommendation", "message": recommendation}
        for recommendation in readiness.get("recommendations", [])
    ]


def _preferred_docs_dir(config: Any, plan: Any) -> str:
    if plan.mkdocs.enabled:
        return plan.mkdocs.docs_dir
    for source in getattr(config, "sources", []):
        path = str(source.get("path", "")).strip()
        source_type = str(source.get("type", "")).strip().lower()
        if path and source_type == "markdown" and not Path(path).suffix:
            return path
    return "docs"


def _check_file(
    root: Path,
    rel_path: str,
    label: str,
    items: list[dict[str, Any]],
    recommendations: list[str],
) -> None:
    path = root / rel_path
    if not path.exists() or not path.is_file():
        items.append(
            {
                "path": rel_path,
                "kind": "file",
                "category": "core",
                "status": "missing",
                "message": f"Missing {label}: {rel_path}",
            }
        )
        recommendations.append(f"Add `{rel_path}` for {label}")
        return
    if path.stat().st_size == 0:
        items.append(
            {
                "path": rel_path,
                "kind": "file",
                "category": "core",
                "status": "empty",
                "message": f"Empty {label}: {rel_path}",
            }
        )
        recommendations.append(f"Fill `{rel_path}` with {label}")
        return
    items.append(
        {
            "path": rel_path,
            "kind": "file",
            "category": "core",
            "status": "ok",
            "message": f"{label} exists: {rel_path}",
        }
    )


def _check_markdown_dir(
    root: Path,
    rel_path: str,
    label: str,
    items: list[dict[str, Any]],
    recommendations: list[str],
) -> None:
    path = root / rel_path
    if not path.exists() or not path.is_dir():
        items.append(
            {
                "path": rel_path,
                "kind": "directory",
                "category": "core",
                "status": "missing",
                "message": f"Missing {label} directory: {rel_path}",
            }
        )
        recommendations.append(f"Create `{rel_path}` for {label}")
        return
    if not any(path.rglob("*.md")):
        items.append(
            {
                "path": rel_path,
                "kind": "directory",
                "category": "core",
                "status": "empty",
                "message": f"No Markdown files found for {label}: {rel_path}",
            }
        )
        recommendations.append(f"Add at least one Markdown file under `{rel_path}` for {label}")
        return
    items.append(
        {
            "path": rel_path,
            "kind": "directory",
            "category": "core",
            "status": "ok",
            "message": f"{label} exists: {rel_path}",
        }
    )


def _join_rel(base: str, suffix: str) -> str:
    base = base.strip().strip("/")
    suffix = suffix.strip().lstrip("/")
    return f"{base}/{suffix}" if base else suffix


def _coverage(items: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(items)
    ok = len([item for item in items if item.get("status") == "ok"])
    categories: dict[str, dict[str, int | float]] = {}
    for item in items:
        category = str(item.get("category") or "core")
        bucket = categories.setdefault(category, {"ok": 0, "total": 0, "percent": 0})
        bucket["total"] = int(bucket["total"]) + 1
        if item.get("status") == "ok":
            bucket["ok"] = int(bucket["ok"]) + 1
    for bucket in categories.values():
        bucket["percent"] = round((int(bucket["ok"]) / max(1, int(bucket["total"]))) * 100, 1)
    return {
        "ok": ok,
        "total": total,
        "percent": round((ok / max(1, total)) * 100, 1),
        "categories": categories,
    }
