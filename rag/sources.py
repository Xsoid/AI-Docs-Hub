from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .mkdocs import MkDocsInfo, build_mkdocs_info


@dataclass(frozen=True)
class SourcePlan:
    sources: list[dict[str, Any]]
    include: list[str]
    exclude: list[str]
    mkdocs: MkDocsInfo
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "sources": self.sources,
            "include": self.include,
            "exclude": self.exclude,
            "mkdocs": self.mkdocs.to_dict(),
            "warnings": self.warnings,
        }


def build_source_plan(config: Any) -> SourcePlan:
    mkdocs = build_mkdocs_info(config)
    sources = [dict(source) for source in getattr(config, "sources", [])]
    include = list(getattr(config, "include", []))
    exclude = list(getattr(config, "exclude", []))

    if mkdocs.enabled:
        sources.append(
            {
                "path": mkdocs.docs_dir or ".",
                "type": "mkdocs",
                "config": mkdocs.config_path,
            }
        )
        include.extend(mkdocs.include)
        exclude.extend(mkdocs.exclude)

    return SourcePlan(
        sources=_dedupe_sources(sources),
        include=_dedupe(include),
        exclude=_dedupe(exclude),
        mkdocs=mkdocs,
        warnings=list(mkdocs.warnings),
    )


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _dedupe_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for source in sources:
        key = (
            str(source.get("path", "")),
            str(source.get("type", "")),
            str(source.get("config", "")),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(source)
    return result
