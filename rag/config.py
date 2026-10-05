from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .yaml_lite import load_yaml
from .mkdocs import DEFAULT_MKDOCS_CONFIG, SUPPORTED_DOCS_BACKENDS


HUB_ROOT = Path(__file__).resolve().parents[1]
CONFIGS_DIR = HUB_ROOT / "configs" / "projects"
INDEX_DIR = HUB_ROOT / "storage" / "index"
PLACEHOLDER_PATH_MARKERS = ("<", "__")
PATH_VARIABLE_RE = re.compile(r"\$(?:\{([A-Za-z_][A-Za-z0-9_]*)\}|([A-Za-z_][A-Za-z0-9_]*))")
DEFAULT_PATH_VARIABLES = {
    "AI_DOCS_HUB_ROOT": HUB_ROOT,
    "AI_DOCS_PROJECTS_ROOT": HUB_ROOT.parent,
}
SCHEMA_VERSION = 1
PROJECT_CONFIG_FIELDS = {
    "schema_version",
    "project",
    "namespace",
    "title",
    "root",
    "docs_backend",
    "mkdocs_config",
    "sources",
    "include",
    "exclude",
    "agent_rules",
}
SOURCE_FIELDS = {"path", "type"}
LIST_FIELDS = {"include", "exclude", "agent_rules"}


class ProjectConfigSchemaError(ValueError):
    """Raised when raw YAML cannot satisfy the project config schema."""

    def __init__(self, path: Path, issues: list[dict[str, str]]) -> None:
        self.path = path
        self.issues = issues
        summary = "; ".join(issue["message"] for issue in issues)
        super().__init__(f"{path}: {summary}")


@dataclass(frozen=True)
class ProjectConfig:
    project: str
    namespace: str
    title: str
    root: Path
    root_source: str
    docs_backend: str
    mkdocs_config: str
    sources: list[dict[str, Any]]
    include: list[str]
    exclude: list[str]
    agent_rules: list[str]
    config_path: Path
    raw: dict[str, Any]
    schema_version: int | None = None

    @property
    def is_legacy(self) -> bool:
        return self.schema_version is None

    @property
    def index_path(self) -> Path:
        return INDEX_DIR / f"{self.project}.json"


def load_project_configs(configs_dir: Path = CONFIGS_DIR) -> dict[str, ProjectConfig]:
    configs: dict[str, ProjectConfig] = {}
    if not configs_dir.exists():
        return configs
    for path in sorted([*configs_dir.glob("*.yaml"), *configs_dir.glob("*.yml")]):
        data = load_yaml(path)
        schema_issues = validate_project_config_schema(data)
        if any(issue["level"] == "error" for issue in schema_issues):
            raise ProjectConfigSchemaError(path, schema_issues)
        config = _config_from_data(path, data)
        configs[config.project] = config
    return configs


def _config_from_data(path: Path, data: dict[str, Any]) -> ProjectConfig:
    project = str(data.get("project", "")).strip()
    root_source = str(data.get("root", "")).strip()
    return ProjectConfig(
        project=project,
        namespace=str(data.get("namespace", project)).strip(),
        title=str(data.get("title", project)).strip(),
        root=resolve_project_root(root_source),
        root_source=root_source,
        docs_backend=str(data.get("docs_backend", "auto") or "auto").strip().lower(),
        mkdocs_config=str(data.get("mkdocs_config", DEFAULT_MKDOCS_CONFIG) or DEFAULT_MKDOCS_CONFIG).strip(),
        sources=list(data.get("sources") or []),
        include=list(data.get("include") or []),
        exclude=list(data.get("exclude") or []),
        agent_rules=list(data.get("agent_rules") or []),
        config_path=path,
        raw=data,
        schema_version=data.get("schema_version"),
    )


def get_project_config(project: str) -> ProjectConfig:
    configs = load_project_configs()
    if project not in configs:
        available = ", ".join(sorted(configs)) or "none"
        raise KeyError(f"Unknown project '{project}'. Available projects: {available}")
    return configs[project]


def validate_project_config(config: ProjectConfig) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if config.is_legacy:
        issues.append(
            {
                "level": "warning",
                "code": "legacy_config",
                "field": "schema_version",
                "message": "Legacy project config without schema_version; add schema_version: 1",
            }
        )
    placeholder_root = is_placeholder_path(config.root_source)
    hardcoded_absolute_root = is_hardcoded_absolute_root(config.root_source)
    if not config.root_source:
        issues.append({"level": "error", "code": "required_field", "field": "root", "message": "root is required"})
    if not config.project:
        issues.append({"level": "error", "code": "required_field", "field": "project", "message": "project is required"})
    if not config.namespace:
        issues.append({"level": "error", "code": "required_field", "field": "namespace", "message": "namespace is required"})
    if config.docs_backend not in SUPPORTED_DOCS_BACKENDS:
        issues.append(
            {
                "level": "error",
                "code": "invalid_enum",
                "field": "docs_backend",
                "message": "docs_backend must be one of: auto, standard, mkdocs",
            }
        )
    if Path(config.mkdocs_config).expanduser().is_absolute():
        issues.append({"level": "warning", "code": "absolute_path", "field": "mkdocs_config", "message": "mkdocs_config should be relative to the project root"})
    if not config.root.is_absolute() and not placeholder_root:
        issues.append({"level": "error", "code": "unsafe_root", "field": "root", "message": "root must resolve to an absolute path"})
    if placeholder_root:
        issues.append({"level": "warning", "code": "unresolved_root", "field": "root", "message": "root is a placeholder or unresolved path"})
    if hardcoded_absolute_root:
        issues.append(
            {
                "level": "warning",
                "code": "hardcoded_absolute_root",
                "field": "root",
                "message": "root should use a portable env variable or relative path instead of a hard-coded absolute path",
            }
        )
    if config.root.exists() and not config.root.is_dir():
        issues.append({"level": "error", "code": "invalid_root", "field": "root", "message": "root exists but is not a directory"})
    if not config.root.exists():
        level = "warning" if placeholder_root else "error"
        issues.append({"level": level, "code": "missing_root", "field": "root", "message": f"root does not exist: {config.root}"})
    if config.root.exists() and config.root.is_dir():
        from .docs_quality import documentation_recommendation_issues
        from .sources import build_source_plan

        source_plan = build_source_plan(config)
        for warning in source_plan.warnings:
            issues.append({"level": "warning", "message": warning})
        if not source_plan.include:
            issues.append({"level": "error", "code": "required_field", "field": "include", "message": "include patterns are required"})
        issues.extend(documentation_recommendation_issues(config))
    elif not config.include:
        issues.append({"level": "error", "code": "required_field", "field": "include", "message": "include patterns are required"})
    return issues


def expand_path_variables(value: str) -> tuple[str, set[str]]:
    unresolved: set[str] = set()

    def replace(match: re.Match[str]) -> str:
        name = match.group(1) or match.group(2) or ""
        if name in os.environ:
            return os.environ[name]
        if name in DEFAULT_PATH_VARIABLES:
            return str(DEFAULT_PATH_VARIABLES[name])
        unresolved.add(name)
        return match.group(0)

    return PATH_VARIABLE_RE.sub(replace, value), unresolved


def resolve_project_root(value: str) -> Path:
    if is_placeholder_path(value):
        return Path(value).expanduser()
    expanded, unresolved = expand_path_variables(value)
    path = Path(expanded).expanduser()
    if unresolved:
        return path
    if not path.is_absolute():
        path = HUB_ROOT / path
    return path.resolve(strict=False)


def is_hardcoded_absolute_root(value: str) -> bool:
    if not value:
        return False
    if PATH_VARIABLE_RE.search(value):
        return False
    if is_placeholder_path(value):
        return False
    return Path(value).expanduser().is_absolute()


def is_placeholder_path(path: Path | str) -> bool:
    value = str(path)
    if PATH_VARIABLE_RE.search(value):
        _, unresolved = expand_path_variables(value)
        if unresolved:
            return True
    return any(marker in value for marker in PLACEHOLDER_PATH_MARKERS)


def is_unbound_example_config(config: ProjectConfig) -> bool:
    return config.project == "example-project" and is_placeholder_path(config.root_source)


def validate_project_config_schema(data: Any) -> list[dict[str, str]]:
    """Validate raw YAML before defaults are applied or ProjectConfig is built."""
    issues: list[dict[str, str]] = []

    def error(code: str, field: str, message: str) -> None:
        issues.append({"level": "error", "code": code, "field": field, "message": message})

    if not isinstance(data, dict):
        error("invalid_type", "", "Project config must be a YAML mapping")
        return issues
    for field in sorted(set(data) - PROJECT_CONFIG_FIELDS):
        error("unknown_field", str(field), f"Unknown project config field: {field}")
    if "schema_version" in data and (type(data["schema_version"]) is not int or data["schema_version"] != SCHEMA_VERSION):
        error("unsupported_schema_version", "schema_version", "schema_version must be integer 1")
    for field in ("project", "root"):
        if field not in data:
            error("required_field", field, f"Missing required project config field: {field}")
        elif not isinstance(data[field], str):
            error("invalid_type", field, f"Project config field '{field}' must be a string")
        elif not data[field].strip():
            error("invalid_value", field, f"Project config field '{field}' must not be empty")
    for field in ("namespace", "title", "docs_backend", "mkdocs_config"):
        if field in data and not isinstance(data[field], str):
            error("invalid_type", field, f"Project config field '{field}' must be a string")
        elif field in data and not data[field].strip():
            error("invalid_value", field, f"Project config field '{field}' must not be empty")
    for field in LIST_FIELDS:
        if field not in data:
            continue
        value = data[field]
        if not isinstance(value, list):
            error("invalid_type", field, f"Project config field '{field}' must be a list")
        else:
            for index, item in enumerate(value):
                if not isinstance(item, str):
                    error("invalid_type", f"{field}[{index}]", f"Project config field '{field}[{index}]' must be a string")
    if "sources" in data:
        sources = data["sources"]
        if not isinstance(sources, list):
            error("invalid_type", "sources", "Project config field 'sources' must be a list")
        else:
            for index, source in enumerate(sources):
                field_prefix = f"sources[{index}]"
                if not isinstance(source, dict):
                    error("invalid_type", field_prefix, f"{field_prefix} must be an object")
                    continue
                for field in sorted(set(source) - SOURCE_FIELDS):
                    error("unknown_field", f"{field_prefix}.{field}", f"Unknown source field: {field}")
                for field in SOURCE_FIELDS:
                    if field not in source:
                        error("required_field", f"{field_prefix}.{field}", f"Missing required source field: {field}")
                    elif not isinstance(source[field], str) or not source[field].strip():
                        error("invalid_type", f"{field_prefix}.{field}", f"{field_prefix}.{field} must be a non-empty string")
    return issues


def _normalized_identity(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def validate_all_configs(configs_dir: Path = CONFIGS_DIR) -> dict[str, list[dict[str, str]]]:
    reports: dict[str, list[dict[str, str]]] = {}
    configs: list[ProjectConfig] = []
    report_keys: dict[Path, str] = {}
    paths = sorted([*configs_dir.glob("*.yaml"), *configs_dir.glob("*.yml")]) if configs_dir.exists() else []
    for path in paths:
        try:
            data = load_yaml(path)
            schema_issues = validate_project_config_schema(data)
            if any(issue["level"] == "error" for issue in schema_issues):
                for issue in schema_issues:
                    issue.setdefault("category", "schema")
                reports[path.stem] = schema_issues
                continue
            config = _config_from_data(path, data)
            report_key = config.project if config.project not in reports else path.stem
            report_keys[path] = report_key
            reports[report_key] = [
                {**issue, "category": issue.get("category", "semantic")}
                for issue in validate_project_config(config)
            ]
            configs.append(config)
        except Exception as exc:
            reports[path.stem] = [{"level": "error", "category": "schema", "code": "yaml_parse_error", "field": "", "message": str(exc)}]
    for identity_field in ("project", "namespace"):
        groups: dict[str, list[ProjectConfig]] = {}
        for config in configs:
            value = getattr(config, identity_field)
            groups.setdefault(_normalized_identity(value), []).append(config)
        for identity, duplicates in sorted(groups.items()):
            if len(duplicates) < 2 or not identity:
                continue
            for config in duplicates:
                reports[report_keys[config.config_path]].append({
                    "level": "error",
                    "category": "semantic",
                    "code": f"duplicate_{identity_field}",
                    "field": identity_field,
                    "message": f"Duplicate {identity_field} after normalization: {identity}",
                })
    return reports
