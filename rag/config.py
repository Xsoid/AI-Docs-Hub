from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .yaml_lite import load_yaml


HUB_ROOT = Path(__file__).resolve().parents[1]
CONFIGS_DIR = HUB_ROOT / "configs" / "projects"
INDEX_DIR = HUB_ROOT / "storage" / "index"


@dataclass(frozen=True)
class ProjectConfig:
    project: str
    namespace: str
    title: str
    root: Path
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
        config = ProjectConfig(
            project=project,
            namespace=str(data.get("namespace", project)).strip(),
            title=str(data.get("title", project)).strip(),
            root=Path(str(data.get("root", ""))).expanduser(),
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
    if not config.namespace:
        issues.append({"level": "error", "message": "namespace is required"})
    if not config.root.is_absolute():
        issues.append({"level": "error", "message": "root must be an absolute path"})
    if "/ABSOLUTE/PATH" in str(config.root):
        issues.append({"level": "warning", "message": "root is a placeholder path"})
    if config.root.exists() and not config.root.is_dir():
        issues.append({"level": "error", "message": "root exists but is not a directory"})
    if not config.root.exists():
        level = "warning" if "/ABSOLUTE/PATH" in str(config.root) else "error"
        issues.append({"level": level, "message": f"root does not exist: {config.root}"})
    if not config.include:
        issues.append({"level": "error", "message": "include patterns are required"})
    return issues


def validate_all_configs() -> dict[str, list[dict[str, str]]]:
    return {
        name: validate_project_config(config)
        for name, config in load_project_configs().items()
    }

