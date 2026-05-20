from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .security import safe_resolve


SUPPORTED_DOCS_BACKENDS = {"auto", "standard", "mkdocs"}
DEFAULT_MKDOCS_CONFIG = "mkdocs.yml"
ALTERNATE_MKDOCS_CONFIG = "mkdocs.yaml"
DEFAULT_MKDOCS_DOCS_DIR = "docs"
DEFAULT_MKDOCS_SITE_DIR = "site"
MKDOCS_PATTERN_KEYS = {"exclude_docs", "draft_docs", "not_in_nav"}
MKDOCS_SCALAR_KEYS = {"site_name", "docs_dir", "site_dir", "INHERIT"}
NAV_PATH_RE = re.compile(r"(?<![:/])([A-Za-z0-9_./-]+\.md)(?:#[A-Za-z0-9_.-]+)?")


@dataclass(frozen=True)
class MkDocsInfo:
    backend: str
    requested: bool
    detected: bool
    enabled: bool
    config_path: str | None
    docs_dir: str
    site_dir: str
    site_name: str | None
    include: list[str]
    exclude: list[str]
    nav_paths: list[str]
    exclude_docs: list[str]
    draft_docs: list[str]
    not_in_nav: list[str]
    inherited_configs: list[str]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class _ParsedMkDocs:
    scalars: dict[str, str | None]
    patterns: dict[str, list[str]]
    nav_paths: list[str]
    nav_seen: bool
    inherited_configs: list[str]
    warnings: list[str]


def docs_backend_from_raw(raw: dict[str, Any]) -> str:
    return str(raw.get("docs_backend", "auto") or "auto").strip().lower()


def mkdocs_config_from_raw(raw: dict[str, Any]) -> str:
    value = str(raw.get("mkdocs_config", DEFAULT_MKDOCS_CONFIG) or DEFAULT_MKDOCS_CONFIG).strip()
    return value or DEFAULT_MKDOCS_CONFIG


def build_mkdocs_info(config: Any) -> MkDocsInfo:
    raw = getattr(config, "raw", {}) or {}
    backend = str(getattr(config, "docs_backend", "") or docs_backend_from_raw(raw)).strip().lower()
    requested = backend == "mkdocs"
    warnings: list[str] = []

    if backend == "standard":
        return _empty_info(backend=backend, requested=False, warnings=[])
    if backend not in SUPPORTED_DOCS_BACKENDS:
        return _empty_info(
            backend=backend,
            requested=requested,
            warnings=[f"unsupported docs_backend '{backend}'; expected auto, standard, or mkdocs"],
        )

    root = getattr(config, "root", None)
    if not isinstance(root, Path) or not root.exists() or not root.is_dir():
        return _empty_info(backend=backend, requested=requested, warnings=[])

    config_rel = str(getattr(config, "mkdocs_config", "") or mkdocs_config_from_raw(raw)).strip()
    config_path = _resolve_config_path(root, config_rel, warnings)
    if config_path is None:
        return _empty_info(backend=backend, requested=requested, warnings=warnings)

    if not config_path.exists() and config_rel == DEFAULT_MKDOCS_CONFIG:
        alternate = root / ALTERNATE_MKDOCS_CONFIG
        if alternate.exists():
            config_path = alternate

    if not config_path.exists():
        if requested:
            warnings.append(
                f"MkDocs config '{config_rel}' was requested but not found; using configured include patterns"
            )
        return _empty_info(backend=backend, requested=requested, warnings=warnings)

    parsed = _load_mkdocs_config(config_path, root, seen=set())
    warnings.extend(parsed.warnings)

    docs_dir = _resolve_project_relative_dir(
        root,
        config_path.parent,
        parsed.scalars.get("docs_dir") or DEFAULT_MKDOCS_DOCS_DIR,
        field_name="docs_dir",
        warnings=warnings,
    )
    site_dir = _resolve_project_relative_dir(
        root,
        config_path.parent,
        parsed.scalars.get("site_dir") or DEFAULT_MKDOCS_SITE_DIR,
        field_name="site_dir",
        warnings=warnings,
    )

    if docs_dir is None:
        return _empty_info(
            backend=backend,
            requested=requested,
            detected=True,
            config_path=_rel_to_root(root, config_path),
            warnings=warnings,
        )

    site_dir = site_dir or DEFAULT_MKDOCS_SITE_DIR
    include = [_join_rel(docs_dir, "**/*.md")]
    exclude = _mkdocs_exclude_patterns(docs_dir, site_dir, parsed, warnings)

    return MkDocsInfo(
        backend=backend,
        requested=requested,
        detected=True,
        enabled=True,
        config_path=_rel_to_root(root, config_path),
        docs_dir=docs_dir,
        site_dir=site_dir,
        site_name=parsed.scalars.get("site_name"),
        include=include,
        exclude=exclude,
        nav_paths=sorted(set(parsed.nav_paths)),
        exclude_docs=parsed.patterns.get("exclude_docs", []),
        draft_docs=parsed.patterns.get("draft_docs", []),
        not_in_nav=parsed.patterns.get("not_in_nav", []),
        inherited_configs=parsed.inherited_configs,
        warnings=warnings,
    )


def _empty_info(
    *,
    backend: str,
    requested: bool,
    detected: bool = False,
    config_path: str | None = None,
    warnings: list[str],
) -> MkDocsInfo:
    return MkDocsInfo(
        backend=backend,
        requested=requested,
        detected=detected,
        enabled=False,
        config_path=config_path,
        docs_dir=DEFAULT_MKDOCS_DOCS_DIR,
        site_dir=DEFAULT_MKDOCS_SITE_DIR,
        site_name=None,
        include=[],
        exclude=[],
        nav_paths=[],
        exclude_docs=[],
        draft_docs=[],
        not_in_nav=[],
        inherited_configs=[],
        warnings=warnings,
    )


def _resolve_config_path(root: Path, config_rel: str, warnings: list[str]) -> Path | None:
    if Path(config_rel).expanduser().is_absolute():
        warnings.append("mkdocs_config must be relative to the project root")
        return None
    try:
        return safe_resolve(root, config_rel)
    except ValueError as exc:
        warnings.append(str(exc))
        return None


def _load_mkdocs_config(path: Path, root: Path, seen: set[Path]) -> _ParsedMkDocs:
    resolved = path.resolve(strict=False)
    if resolved in seen:
        return _ParsedMkDocs(
            scalars={},
            patterns={},
            nav_paths=[],
            nav_seen=False,
            inherited_configs=[],
            warnings=[f"cyclic MkDocs INHERIT detected at {_rel_to_root(root, path)}"],
        )
    seen.add(resolved)

    parsed = _parse_mkdocs_text(path.read_text(encoding="utf-8", errors="replace"))
    inherit = parsed.scalars.get("INHERIT")
    if not inherit:
        return parsed

    parent_path = (path.parent / inherit).resolve(strict=False)
    try:
        parent_path.relative_to(root.resolve())
    except ValueError:
        parsed.warnings.append(
            f"MkDocs INHERIT '{inherit}' points outside the project root and was ignored"
        )
        return parsed

    if not parent_path.exists():
        parsed.warnings.append(f"MkDocs INHERIT parent not found: {inherit}")
        return parsed

    parent = _load_mkdocs_config(parent_path, root, seen)
    merged = _merge_parsed(parent, parsed)
    merged.inherited_configs.append(_rel_to_root(root, parent_path))
    merged.warnings.append(
        "MkDocs INHERIT was resolved for source discovery only; plugins, hooks, and Markdown extensions are not executed"
    )
    return merged


def _parse_mkdocs_text(text: str) -> _ParsedMkDocs:
    blocks = _top_level_blocks(text)
    scalars: dict[str, str | None] = {}
    patterns: dict[str, list[str]] = {}
    nav_paths: list[str] = []
    nav_seen = False
    warnings: list[str] = []

    for key, inline, block in blocks:
        if key in MKDOCS_SCALAR_KEYS:
            scalars[key] = _parse_scalar(inline, warnings, field_name=key)
        elif key in MKDOCS_PATTERN_KEYS:
            patterns[key] = _parse_pattern_list(inline, block, warnings, field_name=key)
        elif key == "nav":
            nav_seen = True
            nav_paths.extend(_extract_nav_paths(block))

    return _ParsedMkDocs(
        scalars=scalars,
        patterns=patterns,
        nav_paths=nav_paths,
        nav_seen=nav_seen,
        inherited_configs=[],
        warnings=warnings,
    )


def _merge_parsed(parent: _ParsedMkDocs, child: _ParsedMkDocs) -> _ParsedMkDocs:
    scalars = dict(parent.scalars)
    for key, value in child.scalars.items():
        if value is not None:
            scalars[key] = value

    patterns = dict(parent.patterns)
    for key, value in child.patterns.items():
        patterns[key] = value

    return _ParsedMkDocs(
        scalars=scalars,
        patterns=patterns,
        nav_paths=child.nav_paths if child.nav_seen else parent.nav_paths,
        nav_seen=parent.nav_seen or child.nav_seen,
        inherited_configs=[*parent.inherited_configs, *child.inherited_configs],
        warnings=[*parent.warnings, *child.warnings],
    )


def _top_level_blocks(text: str) -> list[tuple[str, str, list[str]]]:
    lines: list[tuple[int, str]] = []
    for raw in text.splitlines():
        clean = _strip_comment(raw).rstrip()
        if not clean.strip():
            continue
        indent = len(clean) - len(clean.lstrip(" "))
        lines.append((indent, clean.strip()))

    blocks: list[tuple[str, str, list[str]]] = []
    i = 0
    while i < len(lines):
        indent, current = lines[i]
        if indent != 0:
            i += 1
            continue
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):(?:\s*(.*))?$", current)
        if not match:
            i += 1
            continue
        key = match.group(1)
        inline = match.group(2) or ""
        i += 1
        block: list[str] = []
        while i < len(lines) and lines[i][0] > 0:
            block.append(lines[i][1])
            i += 1
        blocks.append((key, inline.strip(), block))
    return blocks


def _strip_comment(line: str) -> str:
    in_single = False
    in_double = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return line[:i]
    return line


def _parse_scalar(value: str, warnings: list[str], *, field_name: str) -> str | None:
    value = value.strip()
    if not value or value in {"|", ">"}:
        return None
    if value.startswith("!ENV"):
        fallback = _env_tag_fallback(value)
        if fallback is None:
            warnings.append(f"{field_name} uses !ENV without a fallback; it was ignored")
        return fallback
    if value.startswith("!"):
        warnings.append(f"{field_name} uses unsupported YAML tag; it was ignored")
        return None
    if value in {"null", "Null", "NULL", "~"}:
        return None
    return _unquote(value)


def _env_tag_fallback(value: str) -> str | None:
    start = value.find("[")
    end = value.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return None
    parts = [_unquote(part.strip()) for part in value[start + 1 : end].split(",") if part.strip()]
    if len(parts) < 2:
        return None
    return parts[-1]


def _parse_pattern_list(
    inline: str,
    block: list[str],
    warnings: list[str],
    *,
    field_name: str,
) -> list[str]:
    inline = inline.strip()
    values: list[str] = []
    if inline and inline not in {"|", ">"}:
        if inline.startswith("!"):
            warnings.append(f"{field_name} uses unsupported YAML tag; it was ignored")
            return []
        if inline.startswith("[") and inline.endswith("]"):
            values.extend(_unquote(part.strip()) for part in inline[1:-1].split(",") if part.strip())
        else:
            values.append(_unquote(inline))

    for item in block:
        text = item.strip()
        if text.startswith("- "):
            values.append(_unquote(text[2:].strip()))
        elif inline in {"|", ">"}:
            values.append(_unquote(text))

    return [value for value in values if value]


def _extract_nav_paths(block: list[str]) -> list[str]:
    paths: list[str] = []
    for item in block:
        for match in NAV_PATH_RE.findall(item):
            candidate = _unquote(match.strip())
            if candidate.startswith(("http://", "https://", "mailto:")):
                continue
            paths.append(_clean_rel(candidate))
    return paths


def _unquote(value: str) -> str:
    value = value.strip()
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def _resolve_project_relative_dir(
    root: Path,
    config_dir: Path,
    value: str,
    *,
    field_name: str,
    warnings: list[str],
) -> str | None:
    raw_path = Path(value).expanduser()
    if raw_path.is_absolute():
        candidate = raw_path.resolve(strict=False)
    else:
        candidate = (config_dir / raw_path).resolve(strict=False)
    try:
        rel = candidate.relative_to(root.resolve())
    except ValueError:
        warnings.append(f"MkDocs {field_name} points outside the project root and was ignored: {value}")
        return None
    rel_text = _clean_rel(rel.as_posix()).rstrip("/")
    return "" if rel_text == "." else rel_text


def _mkdocs_exclude_patterns(
    docs_dir: str,
    site_dir: str,
    parsed: _ParsedMkDocs,
    warnings: list[str],
) -> list[str]:
    patterns = [
        _join_rel(site_dir, "**"),
        _join_rel(docs_dir, ".*"),
        _join_rel(docs_dir, "**/.*"),
        _join_rel(docs_dir, "templates/**"),
    ]
    for key in ("exclude_docs", "draft_docs"):
        for pattern in parsed.patterns.get(key, []):
            patterns.extend(_translate_mkdocs_pattern(docs_dir, pattern, key, warnings))
    return _dedupe(patterns)


def _translate_mkdocs_pattern(
    docs_dir: str,
    pattern: str,
    key: str,
    warnings: list[str],
) -> list[str]:
    raw = pattern.strip()
    if not raw:
        return []
    if raw.startswith("!"):
        warnings.append(f"MkDocs {key} negated pattern is not applied by the hub: {raw}")
        return []

    anchored = raw.startswith("/")
    pat = _clean_rel(raw.lstrip("/"))
    if not pat:
        return []
    if pat.endswith("/"):
        pat = f"{pat}**"

    if anchored:
        return [_join_rel(docs_dir, pat)]
    if "/" in pat:
        return [_join_rel(docs_dir, pat), _join_rel(docs_dir, f"**/{pat}")]
    return [_join_rel(docs_dir, pat), _join_rel(docs_dir, f"**/{pat}")]


def _join_rel(base: str, suffix: str) -> str:
    base = _clean_rel(base).rstrip("/")
    suffix = _clean_rel(suffix)
    return f"{base}/{suffix}" if base else suffix


def _clean_rel(value: str) -> str:
    text = str(value).replace("\\", "/")
    if text.startswith("./"):
        text = text[2:]
    return text.lstrip("/")


def _rel_to_root(root: Path, path: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
