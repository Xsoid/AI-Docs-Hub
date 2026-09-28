from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .config import HUB_ROOT, ProjectConfig, get_project_config, is_unbound_example_config
from .security import is_excluded, safe_resolve, scan_text_for_secrets


LIFECYCLE_STORAGE_DIR = HUB_ROOT / "storage" / "project-lifecycle"
MAX_COMMAND_OUTPUT = 120_000
DEFAULT_TIMEOUT = 300.0
AGENTS_BEGIN = "<!-- BEGIN AI DOCS HUB PROJECT LIFECYCLE -->"
AGENTS_END = "<!-- END AI DOCS HUB PROJECT LIFECYCLE -->"
SCHEMA_VERSION = 1


class LifecycleError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _storage_dir(project: str) -> Path:
    return LIFECYCLE_STORAGE_DIR / project


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _config(project: str | ProjectConfig) -> ProjectConfig:
    config = get_project_config(project) if isinstance(project, str) else project
    if is_unbound_example_config(config):
        raise LifecycleError(f"{config.project} is an unbound sample config")
    if not config.root.exists() or not config.root.is_dir():
        raise LifecycleError(f"project root does not exist: {config.root}")
    if config.root.resolve() == HUB_ROOT.resolve():
        raise LifecycleError("AI Docs Hub itself cannot be used as an external project")
    return config


def _run_git(root: Path, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=str(root),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    if check and result.returncode != 0:
        raise LifecycleError((result.stderr or result.stdout).strip() or "git command failed")
    return result


def _git_root(root: Path) -> Path:
    result = _run_git(root, ["rev-parse", "--show-toplevel"])
    return Path(result.stdout.strip()).resolve()


def _git_identity(root: Path, project: str) -> str:
    remote = _run_git(root, ["config", "--get", "remote.origin.url"], check=False).stdout.strip()
    return hashlib.sha256(f"{project}\n{remote or root.name}".encode("utf-8")).hexdigest()


def _head(root: Path) -> str | None:
    return _run_git(root, ["rev-parse", "HEAD"], check=False).stdout.strip() or None


def _status_paths(root: Path) -> tuple[list[str], list[str]]:
    result = _run_git(root, ["status", "--porcelain=v1", "--untracked-files=all"])
    tracked: list[str] = []
    untracked: list[str] = []
    for line in result.stdout.splitlines():
        if not line:
            continue
        status = line[:2]
        path = line[3:].strip().strip('"').replace("\\", "/")
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        (untracked if status == "??" else tracked).append(path)
    return sorted(set(tracked)), sorted(set(untracked))


def _scope_args(scope: str, base: str | None) -> list[str]:
    if scope == "working":
        return []
    if scope == "staged":
        return ["--cached"]
    if scope in {"range", "branch"} and base:
        if base.startswith("-") or not re.fullmatch(r"[A-Za-z0-9._/@^~:{}-]+", base):
            raise LifecycleError("base must be a safe git revision ref")
        return [f"{base}...HEAD"]
    if scope in {"range", "branch"}:
        raise LifecycleError(f"--base is required for {scope} scope")
    raise LifecycleError("scope must be working, staged, range, or branch")


def _patch_material(config: ProjectConfig, scope: str, base: str | None) -> tuple[dict[str, Any], bytes, list[str]]:
    root = _git_root(config.root)
    args = _scope_args(scope, base)
    _, untracked = _status_paths(root)
    if scope in {"range", "branch"}:
        name_result = _run_git(root, ["diff", "--name-only", "--no-renames", *args])
        changed = {line.strip() for line in name_result.stdout.splitlines() if line.strip()}
        untracked_for_hash: list[str] = []
    elif scope == "staged":
        name_result = _run_git(root, ["diff", "--cached", "--name-only", "--no-renames"])
        changed = {line.strip() for line in name_result.stdout.splitlines() if line.strip()}
        untracked_for_hash = []
    else:
        unstaged = _run_git(root, ["diff", "--name-only", "--no-renames"])
        staged = _run_git(root, ["diff", "--cached", "--name-only", "--no-renames"])
        changed = (
            {line.strip() for line in unstaged.stdout.splitlines() if line.strip()}
            | {line.strip() for line in staged.stdout.splitlines() if line.strip()}
            | set(untracked)
        )
        untracked_for_hash = sorted({path for path in untracked if not is_excluded(path, [])})
    material = _run_git(root, ["diff", "--no-ext-diff", "--binary", *args]).stdout.encode("utf-8", errors="replace")
    if scope == "working":
        material += _run_git(root, ["diff", "--no-ext-diff", "--binary", "--cached"]).stdout.encode("utf-8", errors="replace")
    for rel_path in untracked_for_hash:
        try:
            content = safe_resolve(root, rel_path).read_bytes()
        except (OSError, ValueError):
            content = b"<unreadable>"
        material += rel_path.encode("utf-8") + b"\0" + content + b"\0"
    metadata = {
        "schema_version": SCHEMA_VERSION,
        "project": config.project,
        "namespace": config.namespace,
        "repository_id": _git_identity(root, config.project),
        "scope": scope,
        "base": base,
        "head": _head(root),
        "changed_files": sorted(changed),
        "untracked_files": untracked_for_hash,
    }
    return metadata, material, sorted(changed)


def patch_fingerprint(config: str | ProjectConfig, *, scope: str = "working", base: str | None = None) -> dict[str, Any]:
    project_config = _config(config)
    metadata, material, changed = _patch_material(project_config, scope, base)
    digest = hashlib.sha256(
        json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\0" + material
    ).hexdigest()
    return {**metadata, "fingerprint": digest, "changed_files": changed}


def _read_json_object(root: Path, name: str) -> dict[str, Any] | None:
    try:
        value = json.loads((root / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def quality_profile(config: str | ProjectConfig, *, persist: bool = True) -> dict[str, Any]:
    project_config = _config(config)
    root = project_config.root.resolve()
    files = {path.name for path in root.iterdir() if path.is_file()}
    languages: list[str] = []
    if any(root.glob("*.py")) or "pyproject.toml" in files or "requirements.txt" in files:
        languages.append("python")
    if "package.json" in files or any(root.glob("*.ts")) or any(root.glob("*.js")):
        languages.append("javascript/typescript")
    if "composer.json" in files or any(root.glob("*.php")):
        languages.append("php")
    if "Cargo.toml" in files:
        languages.append("rust")

    managers: list[str] = []
    package_json = _read_json_object(root, "package.json")
    if package_json:
        managers.append("pnpm" if (root / "pnpm-lock.yaml").is_file() else "yarn" if (root / "yarn.lock").is_file() else "npm")
    if (root / "composer.json").is_file():
        managers.append("composer")
    if (root / "pyproject.toml").is_file() or (root / "requirements.txt").is_file():
        managers.append("python")
    if (root / "Cargo.toml").is_file():
        managers.append("cargo")

    checks: list[dict[str, Any]] = []
    dependency_scanners: list[str] = []
    scripts = (package_json or {}).get("scripts") if package_json else {}
    if isinstance(scripts, dict):
        manager = managers[0] if managers and managers[0] in {"npm", "pnpm", "yarn"} else "npm"
        commands = {
            "lint": ("lint", True),
            "format:check": ("format", False),
            "typecheck": ("typecheck", False),
            "test": ("tests", True),
            "build": ("build", False),
            "audit": ("dependency-security", False),
            "security": ("dependency-security", False),
        }
        for script, (check_id, required) in commands.items():
            if script in scripts:
                prefix = ["npm", "run"] if manager == "npm" else [manager, "run"] if manager == "pnpm" else ["yarn"]
                checks.append({"id": check_id, "command": [*prefix, script], "required": required, "source": "package.json"})
                if check_id == "dependency-security":
                    dependency_scanners.append(f"{manager} run {script}")

    composer = _read_json_object(root, "composer.json")
    composer_scripts = (composer or {}).get("scripts") if composer else {}
    if isinstance(composer_scripts, dict):
        for script, (check_id, required) in {"lint": ("lint", True), "test": ("tests", True), "build": ("build", False), "audit": ("dependency-security", False)}.items():
            if script in composer_scripts:
                checks.append({"id": check_id, "command": ["composer", script], "required": required, "source": "composer.json"})
                if check_id == "dependency-security":
                    dependency_scanners.append(f"composer {script}")

    makefile = root / "Makefile"
    if makefile.is_file():
        targets = set(re.findall(r"^([A-Za-z][A-Za-z0-9_.-]*):", makefile.read_text(encoding="utf-8", errors="replace"), re.MULTILINE))
        for target, (check_id, required) in {"lint": ("lint", True), "typecheck": ("typecheck", False), "test": ("tests", True), "check": ("check", False), "build": ("build", False), "audit": ("dependency-security", False)}.items():
            if target in targets and not any(item["id"] == check_id for item in checks):
                checks.append({"id": check_id, "command": ["make", target], "required": required, "source": "Makefile"})
                if check_id == "dependency-security":
                    dependency_scanners.append(f"make {target}")

    if "pyproject.toml" in files and ((root / "tests").is_dir() or (root / "test").is_dir()) and not any(item["id"] == "tests" for item in checks):
        checks.append({"id": "tests", "command": [sys.executable, "-m", "pytest"], "required": True, "source": "pyproject.toml/tests"})
    if "Cargo.toml" in files:
        for check_id, command, required in (("tests", ["cargo", "test"], True), ("build", ["cargo", "build"], False)):
            if not any(item["id"] == check_id for item in checks):
                checks.append({"id": check_id, "command": command, "required": required, "source": "Cargo.toml"})

    profile = {
        "schema_version": SCHEMA_VERSION,
        "project": project_config.project,
        "namespace": project_config.namespace,
        "generated_at": utc_now(),
        "languages": languages,
        "package_managers": sorted(set(managers)),
        "manifests": sorted(name for name in ("package.json", "composer.json", "pyproject.toml", "Cargo.toml", "Makefile") if (root / name).is_file()),
        "ci_workflows": sorted(path.relative_to(root).as_posix() for path in (root / ".github" / "workflows").glob("*") if path.is_file()) if (root / ".github" / "workflows").is_dir() else [],
        "verification": {"checks": checks},
        "security_surface": {"discovery": "changed-files-and-content", "dependency_scanners": dependency_scanners},
        "source": "project docs, manifests, CI and source-tree metadata",
    }
    if persist:
        _write_json(_storage_dir(project_config.project) / "quality-profile.json", profile)
    return profile


def _bounded_output(stdout: str, stderr: str) -> dict[str, Any]:
    raw = ((stdout or "") + (stderr or "")).encode("utf-8", errors="replace")
    return {"output_bytes": len(raw), "output_sha256": hashlib.sha256(raw).hexdigest(), "output_truncated": len(raw) > MAX_COMMAND_OUTPUT}


def _run_check(root: Path, command: list[str], timeout: float) -> dict[str, Any]:
    started = time.monotonic()
    try:
        result = subprocess.run(command, cwd=str(root), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=False)
        return {"status": "passed" if result.returncode == 0 else "failed", "command": command, "returncode": result.returncode, "duration_ms": round((time.monotonic() - started) * 1000), **_bounded_output(result.stdout, result.stderr)}
    except subprocess.TimeoutExpired as exc:
        return {"status": "error", "reason": f"timeout after {timeout:.0f}s", "command": command, "returncode": 124, "duration_ms": round((time.monotonic() - started) * 1000), **_bounded_output(str(exc.stdout or ""), str(exc.stderr or ""))}
    except OSError as exc:
        return {"status": "error", "reason": str(exc), "command": command, "returncode": 127, "duration_ms": round((time.monotonic() - started) * 1000)}


def _surface(changed_files: Iterable[str], texts: Iterable[str] = ()) -> dict[str, Any]:
    paths = list(changed_files)
    haystack = (" ".join(paths) + "\n" + "\n".join(texts)).lower()
    pattern_map = {
        "authentication": ("auth", "login", "oauth", "password", "credential"),
        "authorization": ("permission", "role", "policy", "acl", "admin"),
        "http": ("http", "route", "endpoint", "controller", "request"),
        "database": ("sql", "query", "orm", "migration", "model", "database"),
        "filesystem": ("upload", "file", "path", "directory"),
        "subprocess": ("subprocess", "shell", "exec", "command"),
        "secrets": (".env", "secret", "token", "key", "credential"),
        "serialization": ("serialize", "deserialize", "pickle", "yaml", "json"),
        "dependency": ("package.json", "composer", "requirements", "pyproject", "cargo", "lock"),
        "ci_cd": (".github/", "workflow", "docker", "deploy", "terraform"),
        "tenant_isolation": ("tenant", "organization", "workspace", "project_id"),
        "logging": ("log", "logger", "audit"),
    }
    found = sorted(name for name, needles in pattern_map.items() if any(needle in haystack for needle in needles))
    docs_only = bool(paths) and all(path.lower().endswith((".md", ".mdx", ".rst", ".txt")) for path in paths)
    if docs_only:
        found = ["docs_only"]
    high = {"authentication", "authorization", "subprocess", "secrets", "dependency", "ci_cd"}
    return {"surface": found, "docs_only": docs_only, "risk_level": "low" if docs_only else "high" if high.intersection(found) else "medium"}


def _secret_check(changed_files: list[str], diff_text: str) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    for path in changed_files:
        if is_excluded(path, []) and any(token in path.lower() for token in (".env", "secret", "token", "password", "credential", "cookie", "session", ".key", ".pem")):
            findings.append({"kind": "secret_looking_path", "path": path})
    for finding in scan_text_for_secrets(diff_text):
        findings.append({"kind": str(finding.get("kind", "secret_pattern")), "line": int(finding.get("line", 0))})
    return {"status": "failed" if findings else "passed", "findings_count": len(findings), "findings": findings[:50], "scanned": "patch metadata and diff only"}


def verify_patch(config: str | ProjectConfig, *, scope: str = "working", base: str | None = None, timeout: float = DEFAULT_TIMEOUT, persist: bool = True) -> dict[str, Any]:
    project_config = _config(config)
    fingerprint = patch_fingerprint(project_config, scope=scope, base=base)
    profile = quality_profile(project_config, persist=persist)
    _, material, changed_files = _patch_material(project_config, scope, base)
    root = _git_root(project_config.root)
    checks: list[dict[str, Any]] = []
    diff_check = _run_check(root, ["git", "diff", "--check", *_scope_args(scope, base)], timeout)
    diff_check["id"] = "git-diff-check"
    checks.append(diff_check)
    if scope == "working":
        staged_check = _run_check(root, ["git", "diff", "--cached", "--check"], timeout)
        staged_check["id"] = "git-diff-check-staged"
        checks.append(staged_check)
    secret = _secret_check(changed_files, material.decode("utf-8", errors="replace"))
    secret["id"] = "secret-scan"
    checks.append(secret)
    for item in profile["verification"]["checks"]:
        command = [str(part) for part in item["command"]]
        if not shutil.which(command[0]):
            checks.append({"id": item["id"], "status": "skipped", "reason": f"tool not available: {command[0]}", "command": command, "required": item.get("required", False)})
            continue
        result = _run_check(project_config.root, command, timeout)
        result.update({"id": item["id"], "required": item.get("required", False), "source": item.get("source")})
        checks.append(result)
    failures = [item for item in checks if item.get("status") in {"failed", "error"} and (item.get("required", True) or item["id"] in {"git-diff-check", "git-diff-check-staged", "secret-scan"})]
    result = {
        "schema_version": SCHEMA_VERSION,
        "project": project_config.project,
        "namespace": project_config.namespace,
        "scope": scope,
        "base": base,
        "fingerprint": fingerprint["fingerprint"],
        "changed_files": changed_files,
        "surface": _surface(changed_files, [material.decode("utf-8", errors="replace")]),
        "checks": checks,
        "status": "failed" if failures else "passed",
        "required_failure_count": len(failures),
        "output_policy": {"max_bytes": MAX_COMMAND_OUTPUT, "stored": "metadata-and-digests-only"},
        "completed_at": utc_now(),
    }
    if persist:
        _write_json(_storage_dir(project_config.project) / "reviews" / fingerprint["fingerprint"] / "verification.json", result)
    return result


def _agents_block(project: str) -> str:
    lines = [
        AGENTS_BEGIN,
        "## AI Docs Hub Project Lifecycle",
        "",
        "- Перед commit, push или PR сначала выполнить Hub pre-publish gate для текущего patch fingerprint.",
        "- Code review и security review относятся к точной версии diff; после изменения patch они становятся stale и повторяются.",
        "- Hub выполняет deterministic verification и хранит local-only metadata; semantic review запускается явно через Codex.",
        "- Не публиковать patch при failed verification, stale/incomplete review или unresolved blocking finding.",
        f"- Для проекта {project} использовать project-scoped Hub tools и не смешивать контекст других проектов.",
        AGENTS_END,
        "",
    ]
    return "\n".join(lines)


def _replace_managed_block(text: str, block: str) -> tuple[str, bool]:
    pattern = re.compile(rf"(?:^|\n){re.escape(AGENTS_BEGIN)}\n.*?\n{re.escape(AGENTS_END)}\n?", re.DOTALL)
    new_text = pattern.sub("\n" + block, text).rstrip() + "\n" if pattern.search(text) else (text.rstrip() + "\n\n" + block if text.strip() else block)
    return new_text, new_text != text


def onboard_project(config: str | ProjectConfig, *, write: bool = False) -> dict[str, Any]:
    project_config = _config(config)
    agents_path = project_config.root.resolve() / "AGENTS.md"
    old_text = agents_path.read_text(encoding="utf-8") if agents_path.is_file() else ""
    new_text, changed = _replace_managed_block(old_text, _agents_block(project_config.project))
    actual = new_text if write and changed else old_text
    if write and changed:
        agents_path.write_text(new_text, encoding="utf-8")
    report = {
        "schema_version": SCHEMA_VERSION,
        "project": project_config.project,
        "namespace": project_config.namespace,
        "status": "initialized" if AGENTS_BEGIN in actual else "missing" if not actual else "attention",
        "agents_exists": agents_path.is_file(),
        "managed_block_present": AGENTS_BEGIN in actual,
        "managed_block_changed": changed,
        "write": write,
        "restart_required": bool(write and changed),
        "native_init": {"status": "unavailable", "reason": "installed Codex CLI has no non-interactive init subcommand"},
        "proposal": "preserve project-owned instructions and review missing repository instructions",
        "agents_fingerprint": hashlib.sha256(actual.encode("utf-8")).hexdigest() if actual else None,
    }
    if write:
        _write_json(_storage_dir(project_config.project) / "init.json", report)
    return report


def prepare_patch_review(config: str | ProjectConfig, *, kind: str, scope: str = "working", base: str | None = None) -> dict[str, Any]:
    if kind not in {"code", "security"}:
        raise LifecycleError("review kind must be code or security")
    project_config = _config(config)
    fingerprint = patch_fingerprint(project_config, scope=scope, base=base)
    profile = quality_profile(project_config, persist=False)
    _, material, changed_files = _patch_material(project_config, scope, base)
    return {
        "schema_version": SCHEMA_VERSION,
        "project": project_config.project,
        "namespace": project_config.namespace,
        "kind": kind,
        "scope": scope,
        "base": base,
        "fingerprint": fingerprint["fingerprint"],
        "changed_files": changed_files,
        "context_budget": {"max_changed_files": 80, "max_doc_results": 8, "max_snippet_chars": 0, "policy": "diff-first; metadata only until Codex explicitly reads scoped sources"},
        "quality_profile": {"languages": profile["languages"], "verification_check_ids": [item["id"] for item in profile["verification"]["checks"]]},
        "security_scope": _surface(changed_files, [material.decode("utf-8", errors="replace")]) if kind == "security" else None,
        "review_contract": "Review current fingerprint only; report findings with path, line, evidence, impact, remediation and confidence.",
    }


def record_review(config: str | ProjectConfig, *, kind: str, scope: str, base: str | None, fingerprint: str, status: str, findings: list[dict[str, Any]], reviewer: str = "codex", summary: str = "") -> dict[str, Any]:
    if kind not in {"code", "security"}:
        raise LifecycleError("review kind must be code or security")
    if status not in {"passed", "failed", "incomplete"}:
        raise LifecycleError("review status must be passed, failed, or incomplete")
    project_config = _config(config)
    current = patch_fingerprint(project_config, scope=scope, base=base)
    if fingerprint != current["fingerprint"]:
        raise LifecycleError("review fingerprint does not match the current patch; prepare a fresh review")
    allowed = ("severity", "confidence", "path", "line", "evidence", "impact", "remediation", "rule", "attack_prerequisite", "asset", "validation")
    normalized = [{key: finding.get(key) for key in allowed if key in finding} for finding in findings if isinstance(finding, dict)]
    record = {
        "schema_version": SCHEMA_VERSION,
        "project": project_config.project,
        "namespace": project_config.namespace,
        "kind": kind,
        "scope": scope,
        "base": base,
        "fingerprint": fingerprint,
        "status": status,
        "reviewed_at": utc_now(),
        "reviewer": reviewer,
        "summary": summary or ("no findings in reviewed scope" if status == "passed" else "review requires follow-up"),
        "findings": normalized,
        "finding_count": len(normalized),
        "security_language_policy": "no absolute security guarantee" if kind == "security" else None,
    }
    _write_json(_storage_dir(project_config.project) / "reviews" / fingerprint / f"{kind}-review.json", record)
    return record


def _current_review(config: ProjectConfig, kind: str, scope: str, base: str | None, fingerprint: str) -> dict[str, Any] | None:
    record = _read_json(_storage_dir(config.project) / "reviews" / fingerprint / f"{kind}-review.json")
    return record if record and record.get("fingerprint") == fingerprint and record.get("scope") == scope and record.get("base") == base else None


def pre_publish_status(config: str | ProjectConfig, *, scope: str = "working", base: str | None = None) -> dict[str, Any]:
    project_config = _config(config)
    fingerprint = patch_fingerprint(project_config, scope=scope, base=base)
    changed = fingerprint["changed_files"]
    if not changed:
        return {"schema_version": SCHEMA_VERSION, "project": project_config.project, "namespace": project_config.namespace, "scope": scope, "fingerprint": fingerprint["fingerprint"], "state": "NO_PATCH", "publishable": False, "blocking_reasons": ["no patch in selected scope"], "changed_files": []}
    review_dir = _storage_dir(project_config.project) / "reviews" / fingerprint["fingerprint"]
    verification = _read_json(review_dir / "verification.json")
    if verification and (verification.get("fingerprint") != fingerprint["fingerprint"] or verification.get("scope") != scope or verification.get("base") != base):
        verification = None
    code = _current_review(project_config, "code", scope, base, fingerprint["fingerprint"])
    security = _current_review(project_config, "security", scope, base, fingerprint["fingerprint"])
    reasons: list[str] = []
    if not verification:
        state, reason = "VERIFYING", "deterministic verification is missing"
    elif verification.get("status") != "passed":
        state, reason = "VERIFICATION_FAILED", "required deterministic verification failed or errored"
    elif not code:
        state, reason = "CODE_REVIEW_REQUIRED", "code review is missing for current fingerprint"
    elif code.get("status") != "passed" or any(str(item.get("severity", "")).lower() in {"blocker", "major", "critical", "high"} for item in code.get("findings", [])):
        state, reason = "CODE_REVIEW_FAILED", "code review has unresolved blocking findings or is incomplete"
    elif not security:
        state, reason = "SECURITY_REVIEW_REQUIRED", "security review is missing for current fingerprint"
    elif security.get("status") != "passed" or any(str(item.get("severity", "")).lower() in {"critical", "high"} for item in security.get("findings", [])):
        state, reason = "SECURITY_REVIEW_FAILED", "security review has unresolved critical/high findings or is incomplete"
    else:
        state, reason = "PUBLISHABLE", ""
    if reason:
        reasons.append(reason)
    return {
        "schema_version": SCHEMA_VERSION,
        "project": project_config.project,
        "namespace": project_config.namespace,
        "scope": scope,
        "base": base,
        "fingerprint": fingerprint["fingerprint"],
        "state": state,
        "publishable": state == "PUBLISHABLE",
        "changed_files": changed,
        "verification": {"status": verification.get("status") if verification else "missing", "completed_at": verification.get("completed_at") if verification else None},
        "code_review": {"status": code.get("status") if code else "missing", "reviewed_at": code.get("reviewed_at") if code else None, "finding_count": code.get("finding_count", 0) if code else 0},
        "security_review": {"status": security.get("status") if security else "missing", "reviewed_at": security.get("reviewed_at") if security else None, "finding_count": security.get("finding_count", 0) if security else 0},
        "blocking_reasons": reasons,
        "stale_rule": "any relevant byte change produces a new fingerprint and requires verification and reviews again",
    }


def lifecycle_status(config: str | ProjectConfig, *, scope: str = "working", base: str | None = None) -> dict[str, Any]:
    project_config = _config(config)
    init = _read_json(_storage_dir(project_config.project) / "init.json") or onboard_project(project_config, write=False)
    try:
        gate = pre_publish_status(project_config, scope=scope, base=base)
    except LifecycleError as exc:
        gate = {"state": "ERROR", "publishable": False, "blocking_reasons": [str(exc)]}
    profile = _read_json(_storage_dir(project_config.project) / "quality-profile.json")
    return {"project": project_config.project, "namespace": project_config.namespace, "init": init, "quality_profile": {"status": "available" if profile else "missing", "generated_at": profile.get("generated_at") if profile else None}, "gate": gate}


def main(argv: list[str] | None = None, forced_command: str | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Project Lifecycle / Quality Gate commands")
    if forced_command:
        command = forced_command
    else:
        parser.add_argument("command", choices=["onboard", "quality-profile", "verify-patch", "prepare-review", "pre-publish", "review-status"])
        command = None
    parser.add_argument("--project", required=True)
    parser.add_argument("--scope", choices=["working", "staged", "range", "branch"], default="working")
    parser.add_argument("--base")
    parser.add_argument("--kind", choices=["code", "security"], default="code")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    command = command or args.command
    try:
        if command == "onboard":
            payload = onboard_project(args.project, write=args.write)
        elif command == "quality-profile":
            payload = quality_profile(args.project)
        elif command == "verify-patch":
            payload = verify_patch(args.project, scope=args.scope, base=args.base, timeout=args.timeout)
        elif command == "prepare-review":
            payload = prepare_patch_review(args.project, kind=args.kind, scope=args.scope, base=args.base)
        else:
            payload = lifecycle_status(args.project, scope=args.scope, base=args.base)
            if command == "pre-publish":
                payload = payload["gate"]
    except (LifecycleError, ValueError, OSError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0
