from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

from .config import CONFIGS_DIR, HUB_ROOT, ProjectConfig, load_project_configs, validate_project_config


PROJECT_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")
NAMESPACE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,127}$")
EDITABLE_FIELDS = {
    "title",
    "namespace",
    "root",
    "docs_backend",
    "mkdocs_config",
    "include",
    "exclude",
}
DEFAULT_INCLUDE = ["README.md", "AGENTS.md", "docs/**/*.md"]
DEFAULT_EXCLUDE = [
    ".git/**",
    ".codex/**",
    "node_modules/**",
    "vendor/**",
    "storage/**",
    "cache/**",
    "tmp/**",
    "logs/**",
    ".env",
    ".env.*",
    "**/.env",
    "**/.env.*",
    "**/*secret*",
    "**/*token*",
    "**/*password*",
    "**/*credential*",
    "**/*cookie*",
    "**/*session*",
    "**/*dump*",
    "**/*.key",
    "**/*.pem",
    "**/*.p12",
    "**/*.pfx",
]


class ProjectConfigEditError(ValueError):
    pass


class ProjectArtifactRefreshError(RuntimeError):
    pass


def _string(value: Any, field: str, *, required: bool = True, limit: int = 4096) -> str:
    if not isinstance(value, str):
        raise ProjectConfigEditError(f"{field} must be a string")
    normalized = value.strip()
    if required and not normalized:
        raise ProjectConfigEditError(f"{field} is required")
    if len(normalized) > limit or "\x00" in normalized or "\n" in normalized or "\r" in normalized:
        raise ProjectConfigEditError(f"{field} contains invalid data")
    return normalized


def _patterns(value: Any, field: str, *, required: bool = False) -> list[str]:
    if not isinstance(value, list):
        raise ProjectConfigEditError(f"{field} must be a list")
    result: list[str] = []
    for item in value:
        pattern = _string(item, field, limit=512)
        if pattern not in result:
            result.append(pattern)
    if required and not result:
        raise ProjectConfigEditError(f"{field} must contain at least one pattern")
    return result


def _quote(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def dump_project_yaml(data: dict[str, Any]) -> str:
    lines: list[str] = []
    for key, value in data.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                if isinstance(item, dict):
                    entries = list(item.items())
                    if not entries:
                        continue
                    first_key, first_value = entries[0]
                    lines.append(f"  - {first_key}: {_quote(first_value)}")
                    for nested_key, nested_value in entries[1:]:
                        lines.append(f"    {nested_key}: {_quote(nested_value)}")
                else:
                    lines.append(f"  - {_quote(item)}")
            lines.append("")
        else:
            lines.append(f"{key}: {_quote(value)}")
    return "\n".join(lines).rstrip() + "\n"


def _validated_payload(payload: dict[str, Any], *, creating: bool) -> tuple[str, dict[str, Any]]:
    project = _string(payload.get("project"), "project", limit=63)
    if not PROJECT_RE.fullmatch(project):
        raise ProjectConfigEditError("project must use lowercase letters, numbers and hyphens")
    namespace = _string(payload.get("namespace", project), "namespace", limit=128)
    if not NAMESPACE_RE.fullmatch(namespace):
        raise ProjectConfigEditError("namespace contains unsupported characters")
    title = _string(payload.get("title", project), "title", limit=120)
    root = _string(payload.get("root"), "root")
    docs_backend = _string(payload.get("docs_backend", "auto"), "docs_backend", limit=16).lower()
    if docs_backend not in {"auto", "standard", "mkdocs"}:
        raise ProjectConfigEditError("docs_backend must be auto, standard or mkdocs")
    mkdocs_config = _string(payload.get("mkdocs_config", "mkdocs.yml"), "mkdocs_config", limit=512)
    include = _patterns(payload.get("include", DEFAULT_INCLUDE if creating else []), "include", required=True)
    requested_exclude = _patterns(payload.get("exclude", []), "exclude")
    exclude = list(dict.fromkeys([*DEFAULT_EXCLUDE, *requested_exclude])) if creating else requested_exclude
    return project, {
        "namespace": namespace,
        "title": title,
        "root": root,
        "docs_backend": docs_backend,
        "mkdocs_config": mkdocs_config,
        "include": include,
        "exclude": exclude,
    }


def save_project_config(
    payload: dict[str, Any],
    *,
    mode: str,
    configs_dir: Path = CONFIGS_DIR,
) -> ProjectConfig:
    if mode not in {"create", "update"}:
        raise ProjectConfigEditError("mode must be create or update")
    configs_dir = configs_dir.resolve()
    configs_dir.mkdir(parents=True, exist_ok=True)
    existing = load_project_configs(configs_dir)
    project, editable = _validated_payload(payload, creating=mode == "create")

    if mode == "create" and project in existing:
        raise ProjectConfigEditError(f"project already exists: {project}")
    if mode == "update" and project not in existing:
        raise ProjectConfigEditError(f"unknown project: {project}")

    if mode == "update":
        current = existing[project]
        data = dict(current.raw)
        path = current.config_path.resolve()
    else:
        data = {
            "schema_version": 1,
            "project": project,
            "namespace": project,
            "title": project,
            "root": payload.get("root", ""),
            "docs_backend": "auto",
            "mkdocs_config": "mkdocs.yml",
            "sources": [
                {"path": "docs", "type": "markdown"},
                {"path": "README.md", "type": "markdown"},
                {"path": "AGENTS.md", "type": "markdown"},
            ],
            "include": list(DEFAULT_INCLUDE),
            "exclude": list(DEFAULT_EXCLUDE),
            "agent_rules": [
                f"Искать только в namespace {project}.",
                "Не использовать контекст других проектов без прямого запроса.",
                "Не читать и не индексировать секреты, ключи, токены, cookies, sessions и дампы.",
            ],
        }
        path = (configs_dir / f"{project}.yaml").resolve()

    if path.parent != configs_dir:
        raise ProjectConfigEditError("project config path escapes configs/projects")
    for field in EDITABLE_FIELDS:
        data[field] = editable[field]
    data["project"] = project
    data["schema_version"] = 1

    serialized = dump_project_yaml(data)
    with tempfile.TemporaryDirectory(prefix="ai-docs-project-config-") as validation_dir:
        candidate_path = Path(validation_dir) / f"{project}.yaml"
        candidate_path.write_text(serialized, encoding="utf-8")
        saved = load_project_configs(Path(validation_dir)).get(project)
        if saved is None:
            raise ProjectConfigEditError("project config could not be reloaded")
        errors = [issue for issue in validate_project_config(saved) if issue.get("level") == "error"]
        structural_errors = [issue for issue in errors if not str(issue.get("message", "")).startswith("root does not exist:")]
        if structural_errors:
            raise ProjectConfigEditError(structural_errors[0]["message"])

    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(serialized, encoding="utf-8")
    try:
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    return load_project_configs(configs_dir)[project]


def exclude_project_paths(project: str, paths: list[str], *, configs_dir: Path = CONFIGS_DIR) -> list[str]:
    """Add exact safe project-relative paths to a Hub config's excludes.

    This is used only to quarantine files already blocked by the secret scanner.
    It never edits the connected project or accepts paths outside its root.
    """
    configs_dir = configs_dir.resolve()
    configs = load_project_configs(configs_dir)
    config = configs.get(project)
    if config is None:
        raise ProjectConfigEditError(f"unknown project: {project}")

    normalized: list[str] = []
    for value in paths:
        candidate = _string(value, "exclude", limit=512).replace("\\", "/")
        pure = Path(candidate)
        if pure.is_absolute() or ".." in pure.parts:
            raise ProjectConfigEditError("blocked source path escapes project root")
        try:
            resolved = (config.root / pure).resolve(strict=True)
            resolved.relative_to(config.root.resolve())
        except (OSError, ValueError):
            raise ProjectConfigEditError("blocked source path is not a project file") from None
        if candidate not in normalized:
            normalized.append(candidate)

    current_exclude = list(config.raw.get("exclude", []))
    additions = [path for path in normalized if path not in current_exclude]
    if not additions:
        return []

    data = dict(config.raw)
    data["exclude"] = [*current_exclude, *additions]
    serialized = dump_project_yaml(data)
    temporary = config.config_path.with_suffix(config.config_path.suffix + ".tmp")
    temporary.write_text(serialized, encoding="utf-8")
    try:
        temporary.replace(config.config_path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return additions


def refresh_project_artifacts(
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> None:
    """Refresh the derived docs that represent all project configs.

    Config YAML is the source of truth; docs-site project pages and llms files
    are derived artifacts.  This is deliberately separate from config writing
    so non-dashboard callers can choose their own refresh boundary.
    """
    for script in ("generate-project-pages", "generate-llms"):
        try:
            result = runner(
                [sys.executable, str(HUB_ROOT / "scripts" / script)],
                cwd=str(HUB_ROOT),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=180,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ProjectArtifactRefreshError("generated documentation refresh failed") from exc
        if result.returncode != 0:
            raise ProjectArtifactRefreshError("generated documentation refresh failed")
