from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .yaml_lite import load_yaml


HUB_ROOT = Path(__file__).resolve().parents[1]
CONFIGS_DIR = HUB_ROOT / "configs" / "projects"
INDEX_DIR = HUB_ROOT / "storage" / "index"
PLACEHOLDER_PATH_MARKERS = ("<", "__")
PATH_VARIABLE_RE = re.compile(r"\$(?:\{([A-Za-z_][A-Za-z0-9_]*)\}|([A-Za-z_][A-Za-z0-9_]*))")
DEFAULT_PATH_VARIABLES = {
    "AI_DOCS_HUB_ROOT": HUB_ROOT,
    "AI_DOCS_PROJECTS_ROOT": HUB_ROOT.parent,
}


@dataclass(frozen=True)
class ProjectConfig:
    project: str
    namespace: str
    title: str
    root: Path
    root_source: str
    sources: list[dict[str, Any]]
    include: list[str]
    exclude: list[str]
    agent_rules: list[str]
    config_path: Path
    raw: dict[str, Any]

    @property
    def index_path(self) -> Path:
        return INDEX_DIR / f"{self.project}.json"


def load_project_configs(configs_dir: Path = CONFIGS_DIR) -> dict[str, ProjectConfig]:
    configs: dict[str, ProjectConfig] = {}
    if not configs_dir.exists():
        return configs
    for path in sorted([*configs_dir.glob("*.yaml"), *configs_dir.glob("*.yml")]):
        data = load_yaml(path)
        project = str(data.get("project", "")).strip()
        if not project:
            raise ValueError(f"{path} is missing required field: project")
        root_source = str(data.get("root", "")).strip()
        config = ProjectConfig(
            project=project,
            namespace=str(data.get("namespace", project)).strip(),
            title=str(data.get("title", project)).strip(),
            root=resolve_project_root(root_source),
            root_source=root_source,
            sources=list(data.get("sources") or []),
            include=list(data.get("include") or []),
            exclude=list(data.get("exclude") or []),
            agent_rules=list(data.get("agent_rules") or []),
            config_path=path,
            raw=data,
        )
        configs[project] = config
    return configs


def get_project_config(project: str) -> ProjectConfig:
    configs = load_project_configs()
    if project not in configs:
        available = ", ".join(sorted(configs)) or "none"
        raise KeyError(f"Unknown project '{project}'. Available projects: {available}")
    return configs[project]


def validate_project_config(config: ProjectConfig) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    placeholder_root = is_placeholder_path(config.root_source)
    hardcoded_absolute_root = is_hardcoded_absolute_root(config.root_source)
    if not config.root_source:
        issues.append({"level": "error", "message": "root is required"})
    if not config.namespace:
        issues.append({"level": "error", "message": "namespace is required"})
    if not config.root.is_absolute() and not placeholder_root:
        issues.append({"level": "error", "message": "root must resolve to an absolute path"})
    if placeholder_root:
        issues.append({"level": "warning", "message": "root is a placeholder or unresolved path"})
    if hardcoded_absolute_root:
        issues.append(
            {
                "level": "warning",
                "message": "root should use a portable env variable or relative path instead of a hard-coded absolute path",
            }
        )
    if config.root.exists() and not config.root.is_dir():
        issues.append({"level": "error", "message": "root exists but is not a directory"})
    if not config.root.exists():
        level = "warning" if placeholder_root else "error"
        issues.append({"level": level, "message": f"root does not exist: {config.root}"})
    if not config.include:
        issues.append({"level": "error", "message": "include patterns are required"})
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


def validate_all_configs() -> dict[str, list[dict[str, str]]]:
    return {
        name: validate_project_config(config)
        for name, config in load_project_configs().items()
    }
