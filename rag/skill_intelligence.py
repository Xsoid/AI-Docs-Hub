from __future__ import annotations

import hashlib
import itertools
import json
import os
import re
import stat
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from .config import HUB_ROOT, ProjectConfig, get_project_config
from .lite import collect_project_files, content_hash
from .logging import log_operation
from .security import is_excluded, safe_resolve, scan_text_for_secrets
from .sources import build_source_plan


SKILL_STORAGE_DIR = HUB_ROOT / "storage" / "skill-intelligence"
SKILL_FILE = "SKILL.md"
MAX_SKILL_LINES = 300
MAX_SOURCE_BYTES = 1_000_000
MIN_CANDIDATE_PROCEDURALITY = 0.35
MIN_REPEATABILITY_PROCEDURALITY = 0.25
ALLOWED_PROPOSAL_ACTIONS = {
    "create_skill",
    "extend_skill",
    "refactor_skill",
    "merge_skills",
    "split_skill",
    "move_skill_content_to_docs",
    "move_agents_content_to_skill",
    "remove_obsolete_rule",
    "no_change",
}
SKILL_TARGET_RE = re.compile(r"^\.agents/skills/[^/]+/SKILL\.md$")
PROCEDURAL_PATTERNS = (
    re.compile(r"(?i)\b(?:first|then|next|before|after|always|never|use|check|run|create|update|verify|ensure)\b"),
    re.compile(r"(?i)(?:сначала|затем|после|перед|всегда|никогда|проверь|проверяй|используй|создай|обнови|убедись|запусти)"),
    re.compile(r"(?i)\b(?:when working on|when changing|for each|before changing|при работе с|при изменении)\b"),
)
TRIGGER_PATTERNS = (
    re.compile(r"(?i)(?:before changing|when changing|when working on|при работе с|при изменении|перед изменением)"),
    re.compile(r"(?i)(?:always|never|must|should|всегда|никогда|обязательно|нельзя)"),
)
FACT_PATTERNS = (
    re.compile(r"(?i)\b(?:uses|is built with|runs on|consists of|использует|построен на|состоит из|запускается на)\b"),
)
GLOBAL_GUARDRAIL_PATTERNS = (
    re.compile(r"(?i)(?:must not|never|prohibited|без прямого разрешения|запрещено|никогда не|не передавай|не публикуй)"),
)
REFERENCE_RE = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)]+)\)|`([^`]+\.(?:md|mdx|ya?ml|toml|json|py|ts|tsx))`")
HOST_PATH_RE = re.compile(r"(?i)(?:/(?:Users|home|private/var)/[^\s`]+|~[/\\][^\s`]+|[A-Z]:\\Users\\[^\s`]+)")
WORKFLOW_TOKEN_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9_]+")
WORKFLOW_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "before", "by", "for", "from", "if",
    "in", "is", "it", "of", "on", "or", "project", "the", "then", "this", "to", "with",
    "а", "без", "в", "для", "если", "и", "из", "как", "на", "не", "по", "при", "с", "со",
    "это", "чтобы", "к", "у", "же", "что",
}
MIN_SHARED_WORKFLOW_TOKENS = 5
MIN_WORKFLOW_SIMILARITY = 0.62


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _storage_project_dir(project: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}", project) or project in {".", ".."}:
        raise ValueError("Project id is not safe for local Skill Intelligence storage")
    hub_root = HUB_ROOT.resolve()
    storage_root = SKILL_STORAGE_DIR.resolve()
    if not storage_root.is_relative_to(hub_root):
        raise ValueError("Skill Intelligence storage must stay inside the AI Docs Hub repository")
    project_dir = SKILL_STORAGE_DIR / project
    if not project_dir.resolve().is_relative_to(storage_root):
        raise ValueError("Skill Intelligence project storage cannot escape its local storage root")
    return project_dir


def _read_source(
    root: Path,
    rel_path: str,
    exclude: Iterable[str] = (),
) -> tuple[str | None, list[dict[str, object]]]:
    if is_excluded(rel_path, exclude):
        return None, [{"kind": "excluded_path"}]
    path = safe_resolve(root, rel_path)
    if not path.is_file():
        return None, [{"kind": "missing_file"}]
    if path.stat().st_size > MAX_SOURCE_BYTES:
        return None, [{"kind": "file_too_large"}]
    text = path.read_text(encoding="utf-8", errors="replace")
    findings = scan_text_for_secrets(text)
    if findings:
        return None, [{"kind": "secret_pattern", "line": finding["line"]} for finding in findings]
    return text, []


def _headings(text: str) -> list[dict[str, Any]]:
    return [
        {"level": len(match.group(1)), "title": match.group(2).strip(), "line": line}
        for line, value in enumerate(text.splitlines(), start=1)
        if (match := re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", value))
    ]


def _normalize_words(value: str) -> str:
    return re.sub(r"\W+", " ", value.casefold()).strip()


def _frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    try:
        end = lines.index("---", 1)
    except ValueError:
        return {}
    values: dict[str, str] = {}
    for line in lines[1:end]:
        match = re.match(r"^([A-Za-z_-]+)\s*:\s*(.*?)\s*$", line)
        if match:
            values[match.group(1)] = match.group(2).strip().strip("'\"")
    return values


def _relative_references(text: str) -> list[str]:
    references: list[str] = []
    for match in REFERENCE_RE.finditer(text):
        reference = (match.group(1) or match.group(2) or "").split("#", 1)[0].strip()
        if not reference or re.match(r"^[a-z]+://", reference, flags=re.IGNORECASE):
            continue
        if reference.startswith(("/", "~")) or re.match(r"^[A-Za-z]:[\\/]", reference):
            references.append(reference)
        elif "." in PurePosixPath(reference).name:
            references.append(reference)
    return references


def _workflow_tokens(text: str) -> list[str]:
    return [
        token
        for token in WORKFLOW_TOKEN_RE.findall(text.casefold())
        if len(token) > 2 and token not in WORKFLOW_STOPWORDS
    ]


def _workflow_similarity(left: str, right: str) -> tuple[float, int]:
    left_tokens = _workflow_tokens(left)
    right_tokens = _workflow_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0, 0
    left_set = set(left_tokens)
    right_set = set(right_tokens)
    shared = len(left_set & right_set)
    union = len(left_set | right_set)
    jaccard = shared / union if union else 0.0
    containment = shared / min(len(left_set), len(right_set))
    # Containment catches a copied workflow wrapped in a longer explanatory
    # section; Jaccard keeps unrelated generic prose from matching easily.
    return round(max(jaccard, containment * 0.82), 3), shared


def _check_skill_references(root: Path, rel_path: str, text: str) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if HOST_PATH_RE.search(text):
        issues.append(
            {
                "type": "absolute_path",
                "severity": "warning",
                "source_path": rel_path,
                "message": "Skill contains a host-specific absolute path",
            }
        )
    parent = PurePosixPath(rel_path).parent
    for reference in _relative_references(text):
        if reference.startswith(("/", "~")) or re.match(r"^[A-Za-z]:[\\/]", reference):
            issues.append(
                {
                    "type": "absolute_path",
                    "severity": "warning",
                    "source_path": rel_path,
                    "message": "Skill contains a host-specific absolute path",
                }
            )
            continue
        normalized = PurePosixPath(parent, reference)
        try:
            target = safe_resolve(root, str(normalized))
        except ValueError:
            issues.append(
                {
                    "type": "path_outside_project",
                    "severity": "error",
                    "source_path": rel_path,
                    "message": "Skill reference escapes the project root",
                    "reference": reference,
                }
            )
            continue
        if not target.exists():
            issues.append(
                {
                    "type": "broken_reference",
                    "severity": "warning",
                    "source_path": rel_path,
                    "message": "Skill reference does not exist",
                    "reference": reference,
                }
            )
    return issues


def _discover_source_paths(config: ProjectConfig) -> list[str]:
    root = config.root.resolve()
    source_plan = build_source_plan(config)
    paths = {
        path.relative_to(root).as_posix()
        for path in collect_project_files(config)
        if path.suffix.lower() in {".md", ".mdx"}
    }
    # These are canonical agent-instruction locations, even when a project's
    # documentation include patterns do not include agent workflow files.
    if (root / "AGENTS.md").is_file():
        paths.add("AGENTS.md")
    skills_dir = root / ".agents" / "skills"
    if skills_dir.is_dir():
        for path in skills_dir.glob(f"*/{SKILL_FILE}"):
            paths.add(path.relative_to(root).as_posix())
    return sorted(
        path
        for path in paths
        if not is_excluded(path, source_plan.exclude)
    )


def _project_excludes(config: ProjectConfig) -> list[str]:
    return build_source_plan(config).exclude


def get_skill_inventory(project: str | ProjectConfig) -> dict[str, Any]:
    config = get_project_config(project) if isinstance(project, str) else project
    root = config.root.resolve()
    skills: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for rel_path in _discover_source_paths(config):
        if not SKILL_FILE == PurePosixPath(rel_path).name or not rel_path.startswith(".agents/skills/"):
            continue
        text, findings = _read_source(root, rel_path)
        if text is None:
            blocked.append({"source_path": rel_path, "findings": findings})
            continue
        frontmatter = _frontmatter(text)
        headings = _headings(text)
        references = _relative_references(text)
        skills.append(
            {
                "name": frontmatter.get("name", ""),
                "description": frontmatter.get("description", ""),
                "path": rel_path,
                "lines": len(text.splitlines()),
                "bytes": len(text.encode("utf-8")),
                "headings": headings,
                "references": references,
                "routing": [
                    heading["title"] for heading in headings
                    if re.search(r"(?i)(route|routing|router|маршрут|выбор)", heading["title"])
                ] + [frontmatter[key] for key in ("routing", "routes_to") if frontmatter.get(key)],
                "dependencies": [
                    reference for reference in references
                    if reference.endswith(("SKILL.md", "AGENTS.md"))
                ] + [
                    frontmatter[key] for key in ("dependencies", "depends_on")
                    if frontmatter.get(key)
                ],
                "scope": [heading["title"] for heading in headings if heading["level"] <= 2],
                "content_hash": content_hash(text),
            }
        )
    names: dict[str, list[str]] = {}
    for skill in skills:
        if skill["name"]:
            names.setdefault(str(skill["name"]).casefold(), []).append(str(skill["path"]))
    duplicate_names = [
        {"name": name, "paths": paths}
        for name, paths in names.items()
        if len(paths) > 1
    ]
    validation_issues = [
        {
            "type": "secret_content",
            "severity": "error",
            "source_path": blocked_source["source_path"],
            "message": "Skill contains secret-looking content and is blocked from analysis",
        }
        for blocked_source in blocked
        if any(
            finding.get("kind") == "secret_pattern"
            for finding in blocked_source["findings"]
        )
    ]
    return {
        "project": config.project,
        "namespace": config.namespace,
        "skills": skills,
        "blocked_sources": blocked,
        "duplicate_names": duplicate_names,
        "validation_issues": validation_issues,
        "count": len(skills),
    }


def _segments(path: str, text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    headings = _headings(text)
    if not headings:
        return [{"source_path": path, "heading": Path(path).stem, "start_line": 1, "end_line": len(lines), "text": text}]
    segments: list[dict[str, Any]] = []
    for index, heading in enumerate(headings):
        start = int(heading["line"])
        end = int(headings[index + 1]["line"]) - 1 if index + 1 < len(headings) else len(lines)
        body = "\n".join(lines[start - 1:end]).strip()
        if body:
            segments.append(
                {
                    "source_path": path,
                    "heading": heading["title"],
                    "start_line": start,
                    "end_line": end,
                    "text": body,
                }
            )
    return segments


def _classify_segment(path: str, segment: dict[str, Any], all_segments: list[dict[str, Any]]) -> dict[str, Any]:
    text = str(segment["text"])
    lines = text.splitlines()
    procedural_hits = sum(bool(pattern.search(text)) for pattern in PROCEDURAL_PATTERNS)
    ordered_steps = sum(bool(re.match(r"^\s*(?:\d+[.)]|[-*+])\s+", line)) for line in lines)
    trigger_hits = sum(bool(pattern.search(text)) for pattern in TRIGGER_PATTERNS)
    fact_hits = sum(bool(pattern.search(text)) for pattern in FACT_PATTERNS)
    is_agents = Path(path).name == "AGENTS.md"
    guardrail = is_agents and any(pattern.search(text) for pattern in GLOBAL_GUARDRAIL_PATTERNS)
    normalized = re.sub(r"\W+", " ", text.lower()).strip()
    similar = [
        item for item in all_segments
        if item is not segment
        and re.sub(r"\W+", " ", str(item["text"]).lower()).strip()[:100] == normalized[:100]
        and normalized
    ]
    procedurality = min(1.0, procedural_hits * 0.24 + min(ordered_steps, 4) * 0.15)
    repeatability = (
        min(1.0, 0.35 + len(similar) * 0.2)
        if procedurality >= MIN_REPEATABILITY_PROCEDURALITY
        else 0.25
    )
    agent_relevance = min(1.0, trigger_hits * 0.35 + (0.25 if is_agents else 0.0))
    stability = 0.75 if procedurality >= MIN_CANDIDATE_PROCEDURALITY else 0.55
    duplication = min(1.0, len(similar) * 0.5)
    if guardrail:
        classification = "global_guardrail"
    elif fact_hits and procedurality < 0.25:
        classification = "canonical_fact"
    elif procedurality >= MIN_CANDIDATE_PROCEDURALITY and (agent_relevance >= 0.25 or ordered_steps >= 2):
        classification = "skill_candidate"
    else:
        classification = "canonical_docs"
    score = round((procedurality + repeatability + agent_relevance + stability + duplication) / 5, 3)
    evidence: list[str] = []
    if procedural_hits:
        evidence.append("imperative_or_procedural_language")
    if ordered_steps:
        evidence.append("checklist_or_ordered_steps")
    if trigger_hits:
        evidence.append("agent_trigger_language")
    if similar:
        evidence.append("repeated_workflow")
    if guardrail:
        evidence.append("global_safety_or_permission_rule")
    return {
        "source_path": path,
        "heading": segment["heading"],
        "start_line": segment["start_line"],
        "end_line": segment["end_line"],
        "classification": classification,
        "scores": {
            "procedurality": round(procedurality, 3),
            "repeatability": round(repeatability, 3),
            "agent_relevance": round(agent_relevance, 3),
            "stability": round(stability, 3),
            "duplication": round(duplication, 3),
            "overall": score,
        },
        "evidence": evidence,
        "source_excerpt": text[:4000],
        "reason": {
            "skill_candidate": "Repeatable, agent-oriented procedure detected; semantic review is still required.",
            "global_guardrail": "This is a global boundary or permission rule and should remain in AGENTS.md.",
            "canonical_fact": "This describes a project fact or contract and belongs in canonical docs.",
            "canonical_docs": "No sufficiently strong reusable workflow signal was detected.",
        }[classification],
    }


def analyze_skill_candidates(
    project: str | ProjectConfig,
    *,
    inventory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = get_project_config(project) if isinstance(project, str) else project
    root = config.root.resolve()
    source_paths = _discover_source_paths(config)
    segments: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for rel_path in source_paths:
        if rel_path.startswith(".agents/skills/") and PurePosixPath(rel_path).name == SKILL_FILE:
            continue
        text, findings = _read_source(root, rel_path)
        if text is None:
            blocked.append({"source_path": rel_path, "findings": findings})
            continue
        segments.extend(_segments(rel_path, text))
    classified = [
        _classify_segment(str(item["source_path"]), item, segments)
        for item in segments
    ]
    inventory = inventory or get_skill_inventory(config)
    for candidate in classified:
        if candidate["classification"] != "skill_candidate":
            continue
        lowered = f"{candidate['heading']} {candidate['source_excerpt']}"
        normalized_text = f" {_normalize_words(lowered)} "
        matching_skills = [
            skill
            for skill in inventory["skills"]
            if f" {_normalize_words(str(skill['name']))} " in normalized_text
        ]
        if matching_skills:
            candidate["target_skill_path"] = matching_skills[0]["path"]
        candidate["action"] = (
            "move_agents_content_to_skill"
            if candidate["source_path"] == "AGENTS.md"
            else "extend_skill" if matching_skills else "create_skill"
        )
    return {
        "project": config.project,
        "namespace": config.namespace,
        "candidates": [item for item in classified if item["classification"] == "skill_candidate"],
        "classifications": classified,
        "blocked_sources": blocked,
        "skill_inventory": inventory,
    }


def _skill_diagnostics(
    config: ProjectConfig,
    inventory: dict[str, Any],
    candidate_analysis: dict[str, Any],
) -> list[dict[str, Any]]:
    root = config.root.resolve()
    issues: list[dict[str, Any]] = list(inventory.get("validation_issues", []))
    canonical_segments: list[dict[str, Any]] = []
    skill_segments: list[dict[str, Any]] = []
    for rel_path in _discover_source_paths(config):
        text, findings = _read_source(root, rel_path, _project_excludes(config))
        if text is None or findings:
            continue
        if rel_path.startswith(".agents/skills/") and PurePosixPath(rel_path).name == SKILL_FILE:
            skill_segments.extend(_segments(rel_path, text))
        else:
            canonical_segments.extend(_segments(rel_path, text))

    name_paths: dict[str, list[str]] = {}
    for skill in inventory["skills"]:
        name = str(skill["name"])
        path = str(skill["path"])
        if name:
            name_paths.setdefault(name.casefold(), []).append(path)
        text, findings = _read_source(root, path)
        if text is None:
            issues.append(
                {
                    "type": "secret_content",
                    "severity": "error",
                    "source_path": path,
                    "message": "Skill contains secret-looking content and is blocked from analysis",
                }
            )
            continue
        frontmatter = _frontmatter(text)
        if not frontmatter.get("name") or not frontmatter.get("description"):
            issues.append(
                {
                    "type": "invalid_frontmatter",
                    "severity": "error",
                    "source_path": path,
                    "message": "SKILL.md frontmatter must include non-empty name and description",
                }
            )
        if not text.strip():
            issues.append(
                {
                    "type": "empty_skill",
                    "severity": "error",
                    "source_path": path,
                    "message": "Skill has no content",
                }
            )
        if int(skill["lines"]) > MAX_SKILL_LINES:
            issues.append(
                {
                    "type": "oversized_skill",
                    "severity": "recommendation",
                    "source_path": path,
                    "message": f"Skill exceeds {MAX_SKILL_LINES} lines; consider splitting responsibilities",
                }
            )
        if skill["routing"]:
            issues.append(
                {
                    "type": "router_skill",
                    "severity": "recommendation",
                    "source_path": path,
                    "message": "Routing-oriented skill found; verify it delegates to focused task-specific skills",
                }
            )
        top_level_headings = [heading for heading in skill["headings"] if heading["level"] <= 2]
        if len(top_level_headings) >= 5:
            issues.append(
                {
                    "type": "mixed_responsibilities",
                    "severity": "recommendation",
                    "source_path": path,
                    "message": "Skill has many top-level sections; consider a router skill and focused sub-skills",
                }
            )
        issues.extend(_check_skill_references(root, path, text))
        duplicate_facts = [
            segment for segment in _segments(path, text)
            if any(pattern.search(str(segment["text"])) for pattern in FACT_PATTERNS)
        ]
        if duplicate_facts:
            issues.append(
                {
                    "type": "possible_fact_duplication",
                    "severity": "warning",
                    "source_path": path,
                    "message": "Skill may contain canonical project facts; verify they are linked from docs instead",
                }
            )
    for name, paths in name_paths.items():
        if len(paths) > 1:
            for path in paths:
                issues.append(
                    {
                        "type": "duplicate_skill_name",
                        "severity": "error",
                        "source_path": path,
                        "message": f"Duplicate skill name: {name}",
                    }
                )
    # Repeated procedures across docs and agent instructions are evidence of
    # duplicated workflow, but do not copy source text into the report. Compare
    # content as well as headings so differently titled copies are detected.
    duplicate_pairs: set[tuple[str, str]] = set()
    candidates = candidate_analysis["candidates"]
    for left, right in itertools.combinations(candidates, 2):
        left_path = str(left["source_path"])
        right_path = str(right["source_path"])
        if left_path == right_path:
            continue
        similarity, shared_tokens = _workflow_similarity(
            str(left.get("source_excerpt", "")),
            str(right.get("source_excerpt", "")),
        )
        if shared_tokens < MIN_SHARED_WORKFLOW_TOKENS or similarity < MIN_WORKFLOW_SIMILARITY:
            continue
        pair = tuple(sorted((left_path, right_path)))
        if pair in duplicate_pairs:
            continue
        duplicate_pairs.add(pair)
        left_item, right_item = sorted((left, right), key=lambda item: str(item["source_path"]))
        issues.append(
            {
                "type": "duplicate_workflow",
                "severity": "warning",
                "source_path": str(left_item["source_path"]),
                "related_paths": [str(right_item["source_path"])],
                "related_headings": [str(left_item["heading"]), str(right_item["heading"])],
                "similarity": similarity,
                "shared_tokens": shared_tokens,
                "message": "Similar reusable workflow candidates appear in multiple canonical sources",
            }
        )

    # A skill may repeat a project fact or workflow that should remain
    # canonical in docs/ or AGENTS.md. Report metadata and paths only; never
    # copy project-derived source text into the persisted audit.
    ownership_pairs: set[tuple[str, str]] = set()
    for skill_segment in skill_segments:
        for canonical_segment in canonical_segments:
            skill_path = str(skill_segment["source_path"])
            canonical_path = str(canonical_segment["source_path"])
            similarity, shared_tokens = _workflow_similarity(
                str(skill_segment["text"]),
                str(canonical_segment["text"]),
            )
            if shared_tokens < MIN_SHARED_WORKFLOW_TOKENS or similarity < 0.72:
                continue
            pair = (skill_path, canonical_path)
            if pair in ownership_pairs:
                continue
            ownership_pairs.add(pair)
            issues.append(
                {
                    "type": "skill_docs_ownership_conflict",
                    "severity": "warning",
                    "source_path": skill_path,
                    "related_path": canonical_path,
                    "skill_heading": str(skill_segment["heading"]),
                    "canonical_heading": str(canonical_segment["heading"]),
                    "similarity": similarity,
                    "shared_tokens": shared_tokens,
                    "message": "Skill content overlaps canonical docs; keep project facts in docs and link from the skill",
                }
            )
    return issues


def validate_skill_architecture(project: str | ProjectConfig) -> dict[str, Any]:
    config = get_project_config(project) if isinstance(project, str) else project
    _storage_project_dir(config.project)
    inventory = get_skill_inventory(config)
    candidates = analyze_skill_candidates(config, inventory=inventory)
    issues = _skill_diagnostics(config, inventory, candidates)
    for candidate in candidates["candidates"]:
        if candidate["source_path"] == "AGENTS.md":
            issues.append(
                {
                    "type": "workflow_in_global_agents",
                    "severity": "warning",
                    "source_path": "AGENTS.md",
                    "message": "Task-specific repeatable workflow may belong in .agents/skills/ instead",
                    "heading": candidate["heading"],
                }
            )
    for item in candidates["classifications"]:
        if re.search(r"(?i)(obsolete|deprecated|no longer used|устарел|больше не используется)", str(item.get("source_excerpt", ""))):
            issues.append(
                {
                    "type": "suspicious_obsolete_rule",
                    "severity": "warning",
                    "source_path": item["source_path"],
                    "message": "Source contains a potentially obsolete rule; verify it against current code and canonical docs",
                    "heading": item["heading"],
                }
            )
    if any(issue["severity"] == "error" for issue in issues):
        log_operation(
            config.project,
            "skill_validation_failed",
            {
                "namespace": config.namespace,
                "error_count": sum(issue["severity"] == "error" for issue in issues),
            },
        )
    return {
        "project": config.project,
        "namespace": config.namespace,
        "status": "blocked" if any(issue["severity"] == "error" for issue in issues) else "ok",
        "skills": inventory,
        "issues": issues,
        "candidates": candidates["candidates"],
        "classifications": [
            {key: value for key, value in item.items() if key != "source_excerpt"}
            for item in candidates["classifications"]
        ],
        "summary": {
            "skill_count": inventory["count"],
            "candidate_count": len(candidates["candidates"]),
            "error_count": sum(issue["severity"] == "error" for issue in issues),
            "warning_count": sum(issue["severity"] == "warning" for issue in issues),
            "recommendation_count": sum(issue["severity"] == "recommendation" for issue in issues),
        },
    }


def _local_artifact_path(config: ProjectConfig, kind: str, artifact_id: str | None = None) -> Path:
    base = _storage_project_dir(config.project)
    if kind == "inventory":
        path = base / "inventory.json"
    elif kind == "audit":
        path = base / "audit.json"
    elif kind == "proposal" and artifact_id and re.fullmatch(r"[a-f0-9-]{36}", artifact_id):
        path = base / "proposals" / f"{artifact_id}.json"
    else:
        raise ValueError("Unsupported Skill Intelligence artifact")
    if not path.resolve().is_relative_to(base.resolve()):
        raise ValueError("Skill Intelligence artifact path escapes its project storage directory")
    return path


def _store_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _source_snapshot(config: ProjectConfig) -> dict[str, dict[str, Any]]:
    root = config.root.resolve()
    snapshot: dict[str, dict[str, Any]] = {}
    for rel_path in _discover_source_paths(config):
        try:
            path = safe_resolve(root, rel_path)
            stat_result = path.stat()
        except (OSError, ValueError):
            continue
        if path.is_file():
            snapshot[rel_path] = {
                "mtime": datetime.fromtimestamp(stat_result.st_mtime, timezone.utc).isoformat(),
                "mtime_ns": stat_result.st_mtime_ns,
                "size": stat_result.st_size,
            }
    return snapshot


def _audit_source_changes(config: ProjectConfig, report: dict[str, Any]) -> list[str] | None:
    stored_snapshot = report.get("source_snapshot")
    if not isinstance(stored_snapshot, dict):
        return None
    root = config.root.resolve()
    changed: set[str] = set()
    current_paths = set(_discover_source_paths(config))
    stored_paths = set(str(path) for path in stored_snapshot)
    changed.update(current_paths - stored_paths)
    changed.update(stored_paths - current_paths)
    for rel_path in current_paths & stored_paths:
        metadata = stored_snapshot.get(rel_path)
        if not isinstance(metadata, dict):
            changed.add(rel_path)
            continue
        try:
            current_path = safe_resolve(root, rel_path)
            current_stat = current_path.stat()
            stored_mtime_ns = metadata.get("mtime_ns")
            if stored_mtime_ns is not None:
                if current_stat.st_mtime_ns != int(stored_mtime_ns):
                    changed.add(rel_path)
                continue
            current_mtime = current_stat.st_mtime
            stored_mtime = datetime.fromisoformat(str(metadata.get("mtime"))).timestamp()
        except (OSError, ValueError, TypeError):
            changed.add(rel_path)
            continue
        if abs(current_mtime - stored_mtime) > 1e-6:
            changed.add(rel_path)
    return sorted(changed)


def run_skill_audit(project: str | ProjectConfig, *, persist: bool = True) -> dict[str, Any]:
    config = get_project_config(project) if isinstance(project, str) else project
    _storage_project_dir(config.project)
    log_operation(config.project, "skill_audit_started", {"namespace": config.namespace})
    report = validate_skill_architecture(config)
    report["audited_at"] = _utc_now()
    report["source_snapshot"] = _source_snapshot(config)
    if persist:
        _store_json(_local_artifact_path(config, "inventory"), report["skills"])
        _store_json(_local_artifact_path(config, "audit"), report)
    log_operation(
        config.project,
        "skill_audit_complete",
        {
            "namespace": config.namespace,
            "skill_count": report["summary"]["skill_count"],
            "candidate_count": report["summary"]["candidate_count"],
            "issue_count": len(report["issues"]),
        },
    )
    return report


def get_stored_skill_intelligence_status(project: str | ProjectConfig) -> dict[str, Any]:
    """Read the last persisted audit without re-running project analysis."""
    config = get_project_config(project) if isinstance(project, str) else project
    audit_path = _local_artifact_path(config, "audit")
    base = {
        "status": "missing",
        "freshness": "missing",
        "audit_exists": False,
        "last_audit_at": None,
        "skill_count": 0,
        "candidate_count": 0,
        "high_confidence_candidate_count": 0,
        "error_count": 0,
        "warning_count": 0,
        "recommendation_count": 0,
        "changed_paths": [],
    }
    if not audit_path.is_file():
        return base
    try:
        report = json.loads(audit_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {**base, "status": "error", "freshness": "invalid", "audit_exists": True}
    if report.get("project") != config.project or report.get("namespace") != config.namespace:
        return {**base, "status": "error", "freshness": "invalid", "audit_exists": True}
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    candidates = report.get("candidates") if isinstance(report.get("candidates"), list) else []
    changed_paths = _audit_source_changes(config, report)
    freshness = "unknown" if changed_paths is None else "stale" if changed_paths else "fresh"
    report_status = str(report.get("status", "ok"))
    status = "blocked" if report_status == "blocked" else "stale" if freshness == "stale" else "audited"
    return {
        **base,
        "status": status,
        "freshness": freshness,
        "audit_exists": True,
        "last_audit_at": report.get("audited_at"),
        "skill_count": int(summary.get("skill_count", 0) or 0),
        "candidate_count": int(summary.get("candidate_count", len(candidates)) or 0),
        "high_confidence_candidate_count": sum(
            float((candidate.get("scores") or {}).get("overall", 0)) >= 0.7
            for candidate in candidates
            if isinstance(candidate, dict) and isinstance(candidate.get("scores") or {}, dict)
        ),
        "error_count": int(summary.get("error_count", 0) or 0),
        "warning_count": int(summary.get("warning_count", 0) or 0),
        "recommendation_count": int(summary.get("recommendation_count", 0) or 0),
        "changed_paths": changed_paths or [],
    }


def get_skill_intelligence_summary(project: str | ProjectConfig) -> dict[str, Any]:
    """Return a compact, read-only Skill Intelligence summary for a profile."""
    config = get_project_config(project) if isinstance(project, str) else project
    report = validate_skill_architecture(config)
    summary = report["summary"]
    high_confidence = sum(
        float(candidate.get("scores", {}).get("overall", 0)) >= 0.7
        for candidate in report["candidates"]
    )
    last_audit_at: str | None = None
    audit_path = _local_artifact_path(config, "audit")
    if audit_path.is_file():
        try:
            stored = json.loads(audit_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            stored = {}
        if stored.get("project") == config.project and stored.get("namespace") == config.namespace:
            value = stored.get("audited_at")
            last_audit_at = str(value) if value else None
    return {
        "status": report["status"],
        "inventory_status": "blocked" if report["skills"].get("blocked_sources") else "ok",
        "skill_count": summary["skill_count"],
        "candidate_count": summary["candidate_count"],
        "high_confidence_candidate_count": high_confidence,
        "error_count": summary["error_count"],
        "warning_count": summary["warning_count"],
        "recommendation_count": summary["recommendation_count"],
        "last_audit_at": last_audit_at,
    }


def create_skill_proposal(
    project: str | ProjectConfig,
    *,
    action: str,
    source_references: list[dict[str, Any]],
    target_paths: list[str],
    evidence: list[str],
    confidence: float,
    reason: str,
    constraints: list[str] | None = None,
    expected_canonical_changes: list[str] | None = None,
    validation_requirements: list[str] | None = None,
    proposal_id: str | None = None,
) -> dict[str, Any]:
    config = get_project_config(project) if isinstance(project, str) else project
    if action not in ALLOWED_PROPOSAL_ACTIONS:
        raise ValueError(f"Unsupported proposal action: {action}")
    if not 0 <= confidence <= 1:
        raise ValueError("confidence must be between 0 and 1")
    if not reason.strip():
        raise ValueError("reason is required")
    if not target_paths and action != "no_change":
        raise ValueError("At least one target path is required")
    allowed = [_validate_target_path(path) for path in target_paths]
    if len(set(allowed)) != len(allowed):
        raise ValueError("Proposal target paths must be unique")
    root = config.root.resolve()
    for reference in source_references:
        if not isinstance(reference, dict):
            raise ValueError("Proposal source references must be objects")
        source_path = str(reference.get("source_path", "")).strip()
        if reference.get("type") == "user_correction":
            if not re.fullmatch(r"user-correction:[A-Za-z0-9._-]{1,100}", source_path):
                raise ValueError("User correction source references must use user-correction:<id>")
            continue
        if not source_path or source_path.startswith(("/", "~")) or "\\" in source_path or ".." in PurePosixPath(source_path).parts:
            raise ValueError("Proposal source references must use safe project-relative paths")
        source = safe_resolve(root, source_path)
        if not source.is_file():
            raise FileNotFoundError(f"Proposal source reference does not exist: {source_path}")
        _, findings = _read_source(root, source_path, _project_excludes(config))
        if findings:
            raise PermissionError(f"Proposal source reference is blocked by security policy: {source_path}")
    expected_hashes: dict[str, str] = {}
    for path in allowed:
        target = safe_resolve(root, path)
        if is_excluded(path, _project_excludes(config)):
            raise PermissionError(f"Proposal target is excluded by security policy: {path}")
        if target.exists():
            if not target.is_file():
                raise ValueError(f"Proposal target is not a file: {path}")
            _, findings = _read_source(root, path, _project_excludes(config))
            if findings:
                raise PermissionError(f"Proposal target cannot be safely read: {path}")
            expected_hashes[path] = hashlib.sha256(target.read_bytes()).hexdigest()
    proposal_id = proposal_id or str(uuid.uuid4())
    if not re.fullmatch(r"[a-f0-9-]{36}", proposal_id):
        raise ValueError("proposal_id must be a UUID")
    proposal = {
        "schema_version": 1,
        "project": config.project,
        "namespace": config.namespace,
        "proposal_id": proposal_id,
        "created_at": _utc_now(),
        "action": action,
        "source_references": source_references,
        "target_paths": allowed,
        "evidence": evidence,
        "confidence": round(confidence, 3),
        "reason": reason,
        "constraints": constraints or [
            "Do not add project-derived content to AI Docs Hub.",
            "Preserve canonical facts in project docs and global guardrails in AGENTS.md.",
            "Do not make changes outside the listed target paths.",
        ],
        "expected_canonical_changes": expected_canonical_changes or [],
        "validation_requirements": validation_requirements or [
            "Validate SKILL.md frontmatter, references, and secret safety.",
            "Review the complete diff before applying.",
        ],
        "expected_hashes": expected_hashes,
    }
    path = _local_artifact_path(config, "proposal", proposal_id)
    _store_json(path, proposal)
    log_operation(
        config.project,
        "skill_proposal_created",
        {"namespace": config.namespace, "proposal_id": proposal_id, "action": action},
    )
    return proposal


def get_skill_proposal(project: str | ProjectConfig, proposal_id: str) -> dict[str, Any]:
    config = get_project_config(project) if isinstance(project, str) else project
    path = _local_artifact_path(config, "proposal", proposal_id)
    if not path.is_file():
        raise FileNotFoundError(f"Skill proposal not found: {proposal_id}")
    proposal = json.loads(path.read_text(encoding="utf-8"))
    if proposal.get("project") != config.project or proposal.get("namespace") != config.namespace:
        raise PermissionError("Skill proposal scope does not match this project")
    return proposal


def _validate_target_path(rel_path: str) -> str:
    normalized = str(PurePosixPath(rel_path))
    if normalized != rel_path or normalized.startswith("/") or "\\" in rel_path or ".." in PurePosixPath(normalized).parts:
        raise ValueError(f"Unsafe proposal target path: {rel_path}")
    if normalized == "AGENTS.md" or normalized.startswith("docs/") or SKILL_TARGET_RE.fullmatch(normalized):
        return normalized
    raise PermissionError(f"Proposal target is outside the allowed project surface: {rel_path}")


def apply_skill_proposal(
    project: str | ProjectConfig,
    proposal_id: str,
    *,
    files: dict[str, str] | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    config = get_project_config(project) if isinstance(project, str) else project
    proposal = get_skill_proposal(config, proposal_id)
    targets = [_validate_target_path(path) for path in proposal["target_paths"]]
    if proposal.get("action") == "no_change":
        return {
            "project": config.project,
            "namespace": config.namespace,
            "proposal_id": proposal_id,
            "applied": False,
            "no_change": True,
            "written_paths": [],
        }
    root = config.root.resolve()
    if not confirm:
        return {
            "project": config.project,
            "namespace": config.namespace,
            "proposal_id": proposal_id,
            "requires_confirmation": True,
            "dry_run": True,
            "target_paths": targets,
            "safe_default": "No project files were written because confirm=true was not provided.",
        }
    if not files:
        raise ValueError("files must contain the reviewed replacement content for each proposal target")
    normalized_files = {_validate_target_path(path): content for path, content in files.items()}
    if set(normalized_files) != set(targets):
        raise ValueError("Apply payload must provide exactly the target paths declared by the proposal")

    prepared: list[tuple[str, Path, bytes, bytes | None, str | None, int]] = []
    hub_root = HUB_ROOT.resolve()
    for rel_path, content in normalized_files.items():
        target = safe_resolve(root, rel_path)
        try:
            target.relative_to(hub_root)
        except ValueError:
            pass
        else:
            raise PermissionError("Skill proposal apply cannot write inside the AI Docs Hub repository")
        if is_excluded(rel_path, _project_excludes(config)):
            raise PermissionError(f"Target path is excluded by security policy: {rel_path}")
        raw = content.encode("utf-8")
        if not raw.strip():
            raise ValueError(f"Refusing to write empty content: {rel_path}")
        findings = scan_text_for_secrets(content)
        if findings:
            raise PermissionError(f"Refusing to write secret-looking content: {rel_path}")
        old_bytes: bytes | None = None
        target_mode = 0o644
        if target.exists():
            expected_hash = proposal.get("expected_hashes", {}).get(rel_path)
            if not expected_hash or hashlib.sha256(target.read_bytes()).hexdigest() != expected_hash:
                raise FileExistsError(f"Existing target changed or was not authorized for replacement: {rel_path}")
            old_bytes = target.read_bytes()
            target_mode = stat.S_IMODE(target.stat().st_mode)
        if rel_path.startswith(".agents/skills/") and PurePosixPath(rel_path).name == SKILL_FILE:
            issues = _validate_skill_text(root, rel_path, content)
            errors = [issue for issue in issues if issue["severity"] == "error"]
            if errors:
                raise ValueError(f"Skill validation failed: {errors[0]['message']}")
            frontmatter = _frontmatter(content)
            duplicate = next(
                (
                    skill for skill in get_skill_inventory(config)["skills"]
                    if skill["name"].casefold() == frontmatter["name"].casefold()
                    and skill["path"] != rel_path
                ),
                None,
            )
            if duplicate:
                raise ValueError(f"Skill name already exists at {duplicate['path']}")
        prepared.append(
            (
                rel_path,
                target,
                raw,
                old_bytes,
                proposal.get("expected_hashes", {}).get(rel_path),
                target_mode,
            )
        )

    temporary_paths: list[Path] = []
    replaced: list[tuple[Path, bytes | None]] = []
    try:
        for _, target, raw, _, _, mode in prepared:
            target.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".skill-proposal-", delete=False) as handle:
                handle.write(raw)
                temporary_paths.append(Path(handle.name))
                os.chmod(handle.name, mode)
        for (rel_path, target, _, old_bytes, expected_hash, _), temporary in zip(prepared, temporary_paths):
            if target.exists():
                current_hash = hashlib.sha256(target.read_bytes()).hexdigest()
                if not expected_hash or current_hash != expected_hash:
                    raise FileExistsError(f"Target changed while preparing apply: {rel_path}")
            elif expected_hash:
                raise FileNotFoundError(f"Authorized target disappeared while preparing apply: {rel_path}")
            temporary.replace(target)
            replaced.append((target, old_bytes))
    except Exception:
        for target, old_bytes in reversed(replaced):
            if old_bytes is None:
                target.unlink(missing_ok=True)
            else:
                target.write_bytes(old_bytes)
        raise
    finally:
        for temporary in temporary_paths:
            temporary.unlink(missing_ok=True)

    for rel_path, _, _, _, _, _ in prepared:
        proposal.setdefault("expected_hashes", {})[rel_path] = hashlib.sha256(
            safe_resolve(root, rel_path).read_bytes()
        ).hexdigest()
    _store_json(_local_artifact_path(config, "proposal", proposal_id), proposal)
    log_operation(
        config.project,
        "skill_proposal_applied",
        {
            "namespace": config.namespace,
            "proposal_id": proposal_id,
            "target_count": len(prepared),
            "target_paths": targets,
        },
    )
    return {
        "project": config.project,
        "namespace": config.namespace,
        "proposal_id": proposal_id,
        "applied": True,
        "written_paths": targets,
    }


def _validate_skill_text(root: Path, rel_path: str, text: str) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if scan_text_for_secrets(text):
        issues.append({"type": "secret_content", "severity": "error", "message": "Secret-like content detected"})
    frontmatter = _frontmatter(text)
    if not frontmatter.get("name") or not frontmatter.get("description"):
        issues.append(
            {
                "type": "invalid_frontmatter",
                "severity": "error",
                "message": "SKILL.md frontmatter must include non-empty name and description",
            }
        )
    if not text.strip():
        issues.append({"type": "empty_skill", "severity": "error", "message": "Skill has no content"})
    issues.extend(_check_skill_references(root, rel_path, text))
    return issues


def create_evolution_proposal(
    project: str | ProjectConfig,
    *,
    target_skill_path: str,
    rule: str,
    evidence_type: str,
    evidence_reference: str,
    explicit_user_correction: bool = False,
    temporary_workaround: bool = False,
) -> dict[str, Any]:
    proven_types = {"working_code", "fixed_regression", "verified_test", "user_correction"}
    if evidence_type not in proven_types or not evidence_reference.strip():
        raise ValueError("Evolution requires a verified, referenced evidence type")
    if temporary_workaround:
        raise ValueError("Temporary workarounds are not eligible for Skill evolution")
    target_skill_path = _validate_target_path(target_skill_path)
    if not SKILL_TARGET_RE.fullmatch(target_skill_path):
        raise ValueError("Evolution target must be an existing .agents/skills/<name>/SKILL.md")
    config = get_project_config(project) if isinstance(project, str) else project
    target = safe_resolve(config.root, target_skill_path)
    if not target.is_file():
        raise FileNotFoundError(f"Evolution target skill does not exist: {target_skill_path}")
    source_path = evidence_reference.strip()
    if evidence_type == "user_correction":
        if not explicit_user_correction:
            raise ValueError("User-correction evidence must be explicitly marked")
        if not re.fullmatch(r"user-correction:[A-Za-z0-9._-]{1,100}", source_path):
            raise ValueError("User-correction evidence must use a stable user-correction:<id> reference")
    else:
        if explicit_user_correction:
            raise ValueError("Explicit user corrections must use evidence_type='user_correction'")
        if source_path.startswith(("/", "~")) or "\\" in source_path or ".." in PurePosixPath(source_path).parts:
            raise ValueError("Evolution evidence reference must be a safe project-relative file path")
        evidence_path = safe_resolve(config.root, source_path)
        if not evidence_path.is_file():
            raise FileNotFoundError(f"Evolution evidence file does not exist: {source_path}")
        _, findings = _read_source(config.root, source_path, _project_excludes(config))
        if findings:
            raise PermissionError("Evolution evidence is blocked by security policy")
    confidence = 0.95 if explicit_user_correction else 0.85
    return create_skill_proposal(
        config,
        action="extend_skill",
        source_references=[{"source_path": evidence_reference, "type": evidence_type}],
        target_paths=[target_skill_path],
        evidence=[evidence_type, "explicit_user_correction" if explicit_user_correction else "verified_reusable_rule"],
        confidence=confidence,
        reason=rule,
        constraints=[
            "Promote only a reusable rule supported by verified evidence.",
            "Do not promote one-off values, guesses, or temporary workarounds.",
            "Require explicit review and apply confirmation.",
        ],
        expected_canonical_changes=[rule],
        validation_requirements=["Confirm the evidence still matches working code and canonical project docs."],
    )
