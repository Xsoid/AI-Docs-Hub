from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import HUB_ROOT
from .docs_quality import documentation_readiness
from .security import safe_resolve


TEMPLATE_DIR = HUB_ROOT / "templates" / "project-docs"


def scaffold_project_docs(config: Any, *, write: bool = False, fill_empty: bool = True) -> dict[str, Any]:
    root = getattr(config, "root", None)
    if not isinstance(root, Path) or not root.exists() or not root.is_dir():
        raise ValueError(f"Project root does not exist: {root}")

    readiness = documentation_readiness(config)
    actions = plan_scaffold_actions(config, readiness, fill_empty=fill_empty)
    executed: list[dict[str, Any]] = []

    if write:
        for action in actions:
            executed.append(_execute_action(root, action))
        remaining_readiness = documentation_readiness(config)
    else:
        executed = [_public_action(action, "planned") for action in actions]
        remaining_readiness = readiness

    return {
        "project": getattr(config, "project", ""),
        "namespace": getattr(config, "namespace", ""),
        "root": str(root),
        "write": write,
        "fill_empty": fill_empty,
        "docs_dir": readiness.get("docs_dir", "docs"),
        "coverage_before": readiness.get("coverage", {}),
        "coverage_after": remaining_readiness.get("coverage", {}),
        "actions_count": len(executed),
        "written_count": len([item for item in executed if item.get("status") == "written"]),
        "actions": executed,
        "remaining_recommendations": remaining_readiness.get("recommendations", []),
    }


def plan_scaffold_actions(config: Any, readiness: dict[str, Any], *, fill_empty: bool = True) -> list[dict[str, Any]]:
    docs_dir = str(readiness.get("docs_dir") or "docs")
    docs_dir = "" if docs_dir == "." else docs_dir.strip("/")
    actions: list[dict[str, Any]] = []

    for item in readiness.get("items", []):
        status = item.get("status")
        if status == "ok":
            continue
        if status == "empty" and not fill_empty:
            continue

        path = str(item.get("path", "")).strip()
        kind = str(item.get("kind", "")).strip()
        reason = str(item.get("message", "Documentation scaffold"))

        if kind == "directory":
            actions.append(_mkdir_action(path, reason))
            scaffold_file = _directory_scaffold_file(config, path, docs_dir)
            if scaffold_file:
                actions.append(scaffold_file)
        elif kind == "content":
            actions.append(_docs_home_action(config, _join_rel(docs_dir, "index.md"), reason))
        elif kind == "file":
            file_action = _file_scaffold_action(config, path, reason)
            if file_action:
                actions.append(file_action)

    return _dedupe_actions(actions)


def _execute_action(root: Path, action: dict[str, Any]) -> dict[str, Any]:
    rel_path = str(action.get("path", "")).strip()
    if not rel_path:
        return {**action, "status": "skipped", "message": "empty path"}

    target = safe_resolve(root, rel_path)
    action_type = action.get("action")

    if action_type == "create_directory":
        target.mkdir(parents=True, exist_ok=True)
        return {**action, "status": "written"}

    if action_type in {"create_file", "fill_empty_file"}:
        if target.exists() and target.is_file() and target.stat().st_size > 0:
            result = _public_action(action, "skipped")
            result["message"] = "target already has content"
            return result
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(str(action.get("content", "")), encoding="utf-8")
        return _public_action(action, "written")

    return {**action, "status": "skipped", "message": f"unknown action: {action_type}"}


def _mkdir_action(path: str, reason: str) -> dict[str, Any]:
    return {
        "action": "create_directory",
        "path": path,
        "reason": reason,
    }


def _file_action(path: str, reason: str, content: str) -> dict[str, Any]:
    return {
        "action": "create_file",
        "path": path,
        "reason": reason,
        "content": content,
    }


def _directory_scaffold_file(config: Any, path: str, docs_dir: str) -> dict[str, Any] | None:
    normalized = path.strip("/")
    if normalized == docs_dir:
        return _docs_home_action(config, _join_rel(docs_dir, "index.md"), f"Create landing page for {path or '.'}")

    name = Path(normalized).name
    target = _join_rel(normalized, "index.md")
    if name == "architecture":
        return _file_action(target, "Create architecture documentation starter", _template("architecture.md"))
    if name == "modules":
        return _file_action(target, "Create module documentation starter", _modules_index_template(config))
    if name == "decisions":
        return _file_action(target, "Create architecture decisions starter", _decisions_index_template(config))
    if name == "api":
        return _file_action(target, "Create API documentation starter", _template("api.md"))
    if name == "deployment":
        return _file_action(target, "Create deployment documentation starter", _template("deployment.md"))
    if name == "operations":
        return _file_action(target, "Create operational runbooks starter", _template("operations.md"))
    if name == "infrastructure":
        return _file_action(target, "Create infrastructure documentation starter", _template("infrastructure.md"))
    return None


def _file_scaffold_action(config: Any, path: str, reason: str) -> dict[str, Any] | None:
    normalized = path.strip("/")
    name = Path(normalized).name
    if normalized == "README.md":
        return _file_action(normalized, reason, _readme_template(config))
    if normalized == "AGENTS.md":
        return _file_action(normalized, reason, _template("agent-rules.md"))
    if name == "glossary.md":
        return _file_action(normalized, reason, _template("glossary.md"))
    if name == "configuration.md":
        return _file_action(normalized, reason, _template("configuration.md"))
    if name == "security.md":
        return _file_action(normalized, reason, _template("security.md"))
    if name == "data.md":
        return _file_action(normalized, reason, _template("data.md"))
    if name == "integrations.md":
        return _file_action(normalized, reason, _template("integrations.md"))
    if name == "observability.md":
        return _file_action(normalized, reason, _template("observability.md"))
    if name == "testing.md":
        return _file_action(normalized, reason, _template("testing.md"))
    if name == "troubleshooting.md":
        return _file_action(normalized, reason, _template("troubleshooting.md"))
    if name == "development.md":
        return _file_action(normalized, reason, _template("development.md"))
    if name == "index.md":
        return _docs_home_action(config, normalized, reason)
    return None


def _docs_home_action(config: Any, path: str, reason: str) -> dict[str, Any]:
    return _file_action(path, reason, _docs_home_template(config))


def _template(name: str) -> str:
    return TEMPLATE_DIR.joinpath(name).read_text(encoding="utf-8").rstrip() + "\n"


def _readme_template(config: Any) -> str:
    title = getattr(config, "title", None) or getattr(config, "project", "Project")
    return f"""# {title}

## Назначение

Опишите, какую проблему решает проект и кто его использует.

## Быстрый старт

Опишите минимальные команды для локального запуска и проверки.

## Документация

- `docs/architecture/` - архитектура проекта.
- `docs/modules/` - модули и зоны ответственности.
- `docs/decisions/` - архитектурные решения.
- `docs/api/` - API и интеграционные контракты.
- `docs/deployment/` - деплой и эксплуатация.
- `docs/operations/` - runbooks и регулярные операции.
- `docs/infrastructure/` - инфраструктура и окружения.
- `docs/configuration.md` - конфигурация без секретов.
- `docs/security.md` - безопасность и доступы.
- `docs/data.md` - данные, миграции и retention.
- `docs/integrations.md` - внешние интеграции.
- `docs/observability.md` - logs, metrics, traces и alerts.
- `docs/testing.md` - стратегия тестирования.
- `docs/troubleshooting.md` - диагностика типовых проблем.
- `docs/development.md` - локальная разработка.
- `docs/glossary.md` - термины проекта.

## Безопасность

Не документируйте секреты, токены, cookies, private keys, dumps или реальные значения production-конфигурации.
"""


def _docs_home_template(config: Any) -> str:
    title = getattr(config, "title", None) or getattr(config, "project", "Project")
    return f"""# {title} Documentation

## Разделы

- [Architecture](architecture/)
- [Modules](modules/)
- [Decisions](decisions/)
- [API](api/)
- [Deployment](deployment/)
- [Operations](operations/)
- [Infrastructure](infrastructure/)
- [Configuration](configuration.md)
- [Security](security.md)
- [Data](data.md)
- [Integrations](integrations.md)
- [Observability](observability.md)
- [Testing](testing.md)
- [Troubleshooting](troubleshooting.md)
- [Development](development.md)
- [Glossary](glossary.md)

## Правило

Проектная документация хранится в этом репозитории. Индексы Хаба и `llms*.txt` являются производными артефактами.
"""


def _modules_index_template(config: Any) -> str:
    return """# Modules

## Назначение

Опишите основные модули проекта и границы их ответственности.

| Module | Responsibility | Source |
| --- | --- | --- |
| Example | Replace with a project-specific module. | `src/...` |

## Правила Изменений

Для каждого значимого модуля добавляйте отдельную страницу в этой директории.
"""


def _decisions_index_template(config: Any) -> str:
    return """# Architecture Decisions

## Назначение

Фиксируйте здесь архитектурные решения, которые влияют на устройство проекта, зависимости, runtime, данные или операционные процессы.

## Индекс

| Decision | Status | Date |
| --- | --- | --- |
| Example decision | Proposed | YYYY-MM-DD |

## Шаблон

Используйте `templates/project-docs/decision.md` из AI Docs Hub как основу для новых ADR.
"""


def _join_rel(base: str, suffix: str) -> str:
    base = base.strip().strip("/")
    suffix = suffix.strip().lstrip("/")
    return f"{base}/{suffix}" if base else suffix


def _dedupe_actions(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for action in actions:
        key = (str(action.get("action", "")), str(action.get("path", "")))
        if key in seen:
            continue
        seen.add(key)
        result.append(action)
    return result


def _without_content(action: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in action.items() if key != "content"}


def _public_action(action: dict[str, Any], status: str) -> dict[str, Any]:
    result = _without_content(action)
    result["status"] = status
    if "content" in action:
        result["content_bytes"] = len(str(action.get("content", "")).encode("utf-8"))
    return result
