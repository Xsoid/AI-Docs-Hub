from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .config import STORAGE_DIR


@dataclass(frozen=True)
class ProjectLocation:
    """A storage location keyed by project id: child directories, or files whose name matches `pattern`."""

    path: Path
    pattern: str | None = None

    def entries(self) -> Iterable[tuple[str, Path]]:
        if not self.path.is_dir():
            return
        for child in sorted(self.path.iterdir()):
            if self.pattern is None:
                if child.is_dir():
                    yield child.name, child
                continue
            match = re.fullmatch(self.pattern, child.name)
            if child.is_file() and match:
                yield match.group("project"), child


def project_locations() -> tuple[ProjectLocation, ...]:
    """Every project-scoped location in Hub storage; each module owns its own path."""
    from .config import INDEX_DIR
    from .context_freshness import SNAPSHOT_DIR
    from .decision_engine import STORAGE_DIR as DECISION_ENGINE_DIR
    from .project_lifecycle import LIFECYCLE_STORAGE_DIR
    from .skill_intelligence import SKILL_STORAGE_DIR

    return (
        ProjectLocation(INDEX_DIR, r"(?P<project>.+?)(?:_log\.jsonl|\.json)"),
        ProjectLocation(DECISION_ENGINE_DIR),
        ProjectLocation(LIFECYCLE_STORAGE_DIR),
        ProjectLocation(SKILL_STORAGE_DIR),
        ProjectLocation(SNAPSHOT_DIR),
        # Codebase Memory: _config.db and logs/ are shared, not per project.
        ProjectLocation(STORAGE_DIR / "codebase-memory", r"(?P<project>[^_].*?)\.db(?:-shm|-wal)?"),
        ProjectLocation(STORAGE_DIR / "runtime" / "codebase-memory", r"(?P<project>.+?)\.status\.json"),
    )


def _size(path: Path) -> int:
    if path.is_dir():
        return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())
    return path.stat().st_size


def find_orphans(known_projects: set[str], locations: Iterable[ProjectLocation] | None = None) -> list[dict[str, Any]]:
    """Storage entries whose project id has no project config."""
    orphans = []
    for location in locations if locations is not None else project_locations():
        for project, path in location.entries():
            if project not in known_projects:
                orphans.append({"project": project, "path": path, "bytes": _size(path)})
    return orphans


def remove_orphans(orphans: Iterable[dict[str, Any]], locations: Iterable[ProjectLocation] | None = None) -> list[Path]:
    """Delete orphan entries; refuse anything that is not a direct child of a project location."""
    roots = {location.path.resolve() for location in (locations if locations is not None else project_locations())}
    targets = [Path(item["path"]) for item in orphans]
    for path in targets:
        if path.resolve().parent not in roots:
            raise ValueError(f"refusing to delete outside project storage locations: {path}")
    removed = []
    for path in targets:
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
        else:
            continue
        removed.append(path)
    return removed


def keep_newest(directory: Path, pattern: str, keep: int) -> list[Path]:
    """Delete all but the newest `keep` entries matching pattern, ordered by modification time, then name."""
    if not directory.is_dir():
        return []
    files = sorted(directory.glob(pattern), key=lambda path: (path.stat().st_mtime_ns, path.name))
    stale = files[:-keep] if keep > 0 else files
    for path in stale:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink(missing_ok=True)
    return stale
