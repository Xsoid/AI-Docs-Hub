from __future__ import annotations

import hashlib
import json
import math
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import HUB_ROOT, INDEX_DIR, ProjectConfig, get_project_config, load_project_configs, validate_project_config
from .logging import log_index_complete, log_index_error, log_index_started, log_secret_scan_blocked
from .security import is_excluded, is_included, safe_resolve, scan_text_for_secrets

MAX_FILE_BYTES = 1_000_000
MAX_READ_DOC_BYTES = 250_000
CHUNK_CHARS = 3200
CHUNK_OVERLAP = 300
TOKEN_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9_]+")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def _read_text(path: Path, max_bytes: int = MAX_FILE_BYTES) -> tuple[str, bool]:
    raw = path.read_bytes()
    truncated = len(raw) > max_bytes
    raw = raw[:max_bytes]
    return raw.decode("utf-8", errors="replace"), truncated


def collect_project_files(config: ProjectConfig) -> list[Path]:
    issues = validate_project_config(config)
    errors = [issue for issue in issues if issue["level"] == "error"]
    if errors:
        messages = "; ".join(issue["message"] for issue in errors)
        raise ValueError(f"Invalid project config {config.project}: {messages}")
    if not config.root.exists():
        raise ValueError(
            f"Project root does not exist: {config.root}. "
            "Set root to a resolvable external project path before indexing."
        )

    root = config.root.resolve()
    files: set[Path] = set()
    for pattern in config.include:
        for candidate in root.glob(pattern):
            if candidate.is_file():
                rel = candidate.resolve().relative_to(root).as_posix()
                if not is_excluded(rel, config.exclude):
                    files.add(candidate.resolve())
    return sorted(files)


def check_project_secrets(config: ProjectConfig) -> dict[str, Any]:
    files = collect_project_files(config)
    blocked: list[dict[str, Any]] = []
    scanned: list[str] = []
    root = config.root.resolve()

    for path in files:
        rel = path.relative_to(root).as_posix()
        if is_excluded(rel, config.exclude):
            blocked.append({"source_path": rel, "reason": "excluded_by_path"})
            continue
        text, truncated = _read_text(path)
        findings = scan_text_for_secrets(text)
        if findings:
            blocked.append(
                {
                    "source_path": rel,
                    "reason": "secret_pattern",
                    "findings": findings,
                    "truncated": truncated,
                }
            )
        else:
            scanned.append(rel)

    return {
        "project": config.project,
        "namespace": config.namespace,
        "scanned_count": len(scanned),
        "blocked_count": len(blocked),
        "blocked": blocked,
    }


def _split_long_text(text: str) -> list[str]:
    if len(text) <= CHUNK_CHARS:
        return [text.strip()]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK_CHARS, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(text):
            break
        start = max(0, end - CHUNK_OVERLAP)
    return chunks


def chunk_document(source_path: str, text: str) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    current_heading = Path(source_path).name
    current_lines: list[str] = []

    def flush() -> None:
        body = "\n".join(current_lines).strip()
        if not body:
            return
        for part in _split_long_text(body):
            chunks.append(
                {
                    "heading": current_heading,
                    "section": current_heading,
                    "text": part,
                }
            )

    for line in text.splitlines():
        heading_match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if heading_match:
            flush()
            current_heading = heading_match.group(2).strip()
            current_lines = [line]
        else:
            current_lines.append(line)
    flush()

    if not chunks and text.strip():
        for part in _split_long_text(text):
            chunks.append(
                {
                    "heading": Path(source_path).name,
                    "section": Path(source_path).name,
                    "text": part,
                }
            )
    return chunks


def build_index(config: ProjectConfig, reindex: bool = False) -> dict[str, Any]:
    start_time = time.time()
    log_index_started(config.project, reindex=reindex)
    
    try:
        secret_report = check_project_secrets(config)
        if secret_report["blocked_count"]:
            blocked_files = [f["source_path"] for f in secret_report.get("blocked", [])]
            log_secret_scan_blocked(config.project, secret_report["blocked_count"], blocked_files)
            raise ValueError(
                f"Secret scan blocked indexing for {config.project}: "
                f"{secret_report['blocked_count']} suspicious file(s)"
            )

        if reindex and config.index_path.exists():
            config.index_path.unlink()

        root = config.root.resolve()
        files = collect_project_files(config)
        documents: list[dict[str, Any]] = []
        chunks: list[dict[str, Any]] = []

        for path in files:
            rel = path.relative_to(root).as_posix()
            if not is_included(rel, config.include) or is_excluded(rel, config.exclude):
                continue
            text, truncated = _read_text(path)
            digest = content_hash(text)
            stat = path.stat()
            doc_chunks = chunk_document(rel, text)
            chunk_ids: list[str] = []
            for idx, chunk in enumerate(doc_chunks):
                chunk_id = hashlib.sha1(f"{config.namespace}:{rel}:{idx}:{digest}".encode("utf-8")).hexdigest()
                chunk_ids.append(chunk_id)
                chunks.append(
                    {
                        "chunk_id": chunk_id,
                        "project": config.project,
                        "namespace": config.namespace,
                        "source_path": rel,
                        "heading": chunk["heading"],
                        "section": chunk["section"],
                        "file_mtime": stat.st_mtime,
                        "updated_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                        "content_hash": digest,
                        "text": chunk["text"],
                        "truncated_source": truncated,
                    }
                )
            documents.append(
                {
                    "source_path": rel,
                    "file_mtime": stat.st_mtime,
                    "updated_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    "content_hash": digest,
                    "chunk_ids": chunk_ids,
                    "truncated_source": truncated,
                }
            )

        index = {
            "schema_version": 1,
            "backend": "lite-json-bm25",
            "project": config.project,
            "namespace": config.namespace,
            "title": config.title,
            "root": str(config.root),
            "config_path": str(config.config_path.relative_to(HUB_ROOT)),
            "indexed_at": utc_now(),
            "documents_count": len(documents),
            "chunks_count": len(chunks),
            "documents": documents,
            "chunks": chunks,
        }

        INDEX_DIR.mkdir(parents=True, exist_ok=True)
        config.index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
        
        duration = time.time() - start_time
        log_index_complete(config.project, len(documents), len(chunks), duration)
        return index
    
    except Exception as e:
        duration = time.time() - start_time
        log_index_error(config.project, type(e).__name__, str(e))
        raise


def load_index(project: str) -> dict[str, Any]:
    config = get_project_config(project)
    if not config.index_path.exists():
        raise FileNotFoundError(f"Index not found for project '{project}'. Run: make index PROJECT={project}")
    return json.loads(config.index_path.read_text(encoding="utf-8"))


def search_index(project: str, query: str, limit: int = 8, path_filter: str | None = None) -> dict[str, Any]:
    index = load_index(project)
    chunks = list(index.get("chunks") or [])
    if path_filter:
        path_filter_lower = path_filter.lower()
        chunks = [chunk for chunk in chunks if path_filter_lower in str(chunk.get("source_path", "")).lower()]

    query_terms = tokenize(query)
    if not query_terms:
        return {"project": project, "namespace": index.get("namespace"), "query": query, "results": []}

    doc_freq: dict[str, int] = {}
    chunk_terms: list[tuple[dict[str, Any], list[str]]] = []
    for chunk in chunks:
        terms = tokenize(" ".join([str(chunk.get("heading", "")), str(chunk.get("text", ""))]))
        chunk_terms.append((chunk, terms))
        unique = set(terms)
        for term in set(query_terms):
            if term in unique:
                doc_freq[term] = doc_freq.get(term, 0) + 1

    total = max(1, len(chunks))
    scored: list[dict[str, Any]] = []
    for chunk, terms in chunk_terms:
        if not terms:
            continue
        heading_terms = set(tokenize(str(chunk.get("heading", ""))))
        term_counts: dict[str, int] = {}
        for term in terms:
            term_counts[term] = term_counts.get(term, 0) + 1
        score = 0.0
        for term in query_terms:
            tf = term_counts.get(term, 0)
            if tf == 0:
                continue
            idf = math.log((total + 1) / (doc_freq.get(term, 0) + 1)) + 1
            boost = 1.5 if term in heading_terms else 1.0
            score += (1 + math.log(tf)) * idf * boost
        if score <= 0:
            continue
        confidence = round(min(0.99, score / (score + 6.0)), 3)
        snippet = str(chunk.get("text", "")).strip().replace("\n", " ")
        if len(snippet) > 700:
            snippet = snippet[:697].rstrip() + "..."
        scored.append(
            {
                "score": round(score, 4),
                "confidence": confidence,
                "project": chunk.get("project"),
                "namespace": chunk.get("namespace"),
                "source_path": chunk.get("source_path"),
                "heading": chunk.get("heading"),
                "section": chunk.get("section"),
                "updated_at": chunk.get("updated_at"),
                "content_hash": chunk.get("content_hash"),
                "snippet": snippet,
            }
        )

    scored.sort(key=lambda item: item["score"], reverse=True)
    return {
        "project": project,
        "namespace": index.get("namespace"),
        "query": query,
        "limit": limit,
        "results": scored[: max(1, min(limit, 50))],
    }


def read_project_doc(project: str, source_path: str) -> dict[str, Any]:
    config = get_project_config(project)
    issues = validate_project_config(config)
    errors = [issue for issue in issues if issue["level"] == "error"]
    if errors:
        messages = "; ".join(issue["message"] for issue in errors)
        raise ValueError(f"Invalid project config {project}: {messages}")
    rel = source_path.strip().lstrip("/")
    if is_excluded(rel, config.exclude):
        raise PermissionError(f"Refusing to read excluded path: {source_path}")
    if not is_included(rel, config.include):
        raise PermissionError(f"Path is not allowed by include rules: {source_path}")
    path = safe_resolve(config.root, rel)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Document not found: {source_path}")
    text, truncated = _read_text(path, max_bytes=MAX_READ_DOC_BYTES)
    findings = scan_text_for_secrets(text)
    if findings:
        raise PermissionError(f"Refusing to return content with secret-like patterns: {source_path}")
    stat = path.stat()
    return {
        "project": config.project,
        "namespace": config.namespace,
        "source_path": rel,
        "updated_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "content_hash": content_hash(text),
        "truncated": truncated,
        "content": text,
        "confidence": 1.0,
    }


def list_projects() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for config in load_project_configs().values():
        issues = validate_project_config(config)
        result.append(
            {
                "project": config.project,
                "namespace": config.namespace,
                "title": config.title,
                "root": str(config.root),
                "config_path": str(config.config_path.relative_to(HUB_ROOT)),
                "index_exists": config.index_path.exists(),
                "issues": issues,
            }
        )
    return result


def project_profile(project: str) -> dict[str, Any]:
    config = get_project_config(project)
    return {
        "project": config.project,
        "namespace": config.namespace,
        "title": config.title,
        "root": str(config.root),
        "sources": config.sources,
        "include": config.include,
        "exclude": config.exclude,
        "agent_rules": config.agent_rules,
        "config_path": str(config.config_path.relative_to(HUB_ROOT)),
        "index_path": str(config.index_path.relative_to(HUB_ROOT)),
        "index_exists": config.index_path.exists(),
        "issues": validate_project_config(config),
    }


def search_decisions(project: str, query: str, limit: int = 8) -> dict[str, Any]:
    result = search_index(project, query, limit=limit * 2)
    filtered = [
        item
        for item in result["results"]
        if any(part in str(item.get("source_path", "")).lower() for part in ["decision", "decisions", "adr"])
    ]
    result["results"] = filtered[:limit]
    result["limit"] = limit
    return result


def search_modules(project: str, module_name: str, limit: int = 8) -> dict[str, Any]:
    query = module_name
    result = search_index(project, query, limit=limit * 2)
    module_lower = module_name.lower()
    filtered = [
        item
        for item in result["results"]
        if "module" in str(item.get("source_path", "")).lower()
        or module_lower in str(item.get("source_path", "")).lower()
        or module_lower in str(item.get("heading", "")).lower()
    ]
    if not filtered:
        filtered = result["results"]
    result["results"] = filtered[:limit]
    result["limit"] = limit
    return result
