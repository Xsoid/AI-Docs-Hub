from __future__ import annotations

import fnmatch
import re
from pathlib import Path, PurePosixPath
from typing import Iterable


DEFAULT_EXCLUDE = [
    ".git/**",
    "vendor/**",
    "node_modules/**",
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
    "**/*.key",
    "**/*.pem",
    "**/*.p12",
    "**/*.pfx",
    "**/*cookie*",
    "**/*session*",
    "**/*credential*",
    "**/*dump*",
]

SECRET_PATTERNS = [
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    (
        "assignment_secret",
        re.compile(
            r"(?i)\b(api[_-]?key|secret|token|password|passwd|credential|cookie|session)\b\s*[:=]\s*['\"]?[^\s'\"]{8,}"
        ),
    ),
]


def normalize_rel(path: str | Path) -> str:
    return str(path).replace("\\", "/").lstrip("./")


def matches_any(path: str, patterns: Iterable[str]) -> bool:
    rel = normalize_rel(path)
    rel_lower = rel.lower()
    name_lower = PurePosixPath(rel_lower).name
    for pattern in patterns:
        pat = normalize_rel(pattern).lower()
        variants = {pat}
        if "**/" in pat:
            variants.add(pat.replace("**/", ""))
        for variant in variants:
            if fnmatch.fnmatchcase(rel_lower, variant):
                return True
            if fnmatch.fnmatchcase(name_lower, variant):
                return True
            try:
                if PurePosixPath(rel_lower).match(variant):
                    return True
            except ValueError:
                continue
    return False


def is_excluded(path: str, patterns: Iterable[str]) -> bool:
    return matches_any(path, list(patterns) + DEFAULT_EXCLUDE)


def is_included(path: str, patterns: Iterable[str]) -> bool:
    return matches_any(path, patterns)


def scan_text_for_secrets(text: str) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for kind, pattern in SECRET_PATTERNS:
            if pattern.search(line):
                findings.append({"line": line_number, "kind": kind})
    return findings


def safe_resolve(root: Path, rel_path: str) -> Path:
    root_resolved = root.resolve()
    candidate = (root_resolved / rel_path).resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError(f"Path escapes project root: {rel_path}") from exc
    return candidate
