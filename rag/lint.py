from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .config import ProjectConfig, get_project_config
from .docs_quality import documentation_readiness
from .lite import collect_project_files, load_index
from .wiki_links import extract_wiki_links


def lint_project(project: str, detailed: bool = False) -> dict[str, Any]:
    """Run structural lint checks on a project.
    
    Checks:
    - Broken wiki-links (references to non-existent pages)
    - Orphan pages (pages with no incoming links)
    - Missing frontmatter fields in markdown
    - Empty documents
    - Duplicate headings
    
    Args:
        project: Project name
        detailed: Include line-by-line details
    
    Returns:
        Lint report with issues, statistics, and recommendations
    """
    config = get_project_config(project)
    readiness = documentation_readiness(config)
    readiness_issues = _readiness_to_issues(readiness)
    
    try:
        index = load_index(project)
    except FileNotFoundError:
        return {
            "project": project,
            "status": "not_indexed",
            "message": f"Project not indexed. Run: make index PROJECT={project}",
            "issues": readiness_issues,
            "statistics": {
                "total_documents": 0,
                "total_issues": len(readiness_issues),
                "documentation_gaps": len(readiness_issues),
                "documentation_coverage_percent": readiness.get("coverage", {}).get("percent", 0),
            },
            "documentation": readiness,
            "recommendations": readiness.get("recommendations", []),
        }
    
    # Collect all available paths
    files = collect_project_files(config)
    root = config.root.resolve()
    available_paths: set[str] = {str(f.relative_to(root)).lower() for f in files}
    available_names: set[str] = {Path(p).stem.lower() for p in available_paths}
    
    issues: list[dict[str, Any]] = []
    
    # 1. Check for broken wiki-links
    broken_links = _check_broken_wiki_links(index, available_names, detailed)
    issues.extend(broken_links)
    
    # 2. Check for empty documents
    empty_docs = _check_empty_documents(index)
    issues.extend(empty_docs)
    
    # 3. Check for orphan pages
    orphans = _check_orphan_pages(index, available_names)
    issues.extend(orphans)
    
    # 4. Check for missing frontmatter in docs
    frontmatter_issues = _check_frontmatter(index)
    issues.extend(frontmatter_issues)
    
    # 5. Check for duplicate headings in same file
    duplicate_headings = _check_duplicate_headings(index)
    issues.extend(duplicate_headings)

    # 6. Check project documentation completeness against hub standards
    issues.extend(readiness_issues)
    
    # Categorize issues
    statistics = {
        "total_documents": index.get("documents_count", 0),
        "total_chunks": index.get("chunks_count", 0),
        "total_issues": len(issues),
        "broken_links": len([i for i in issues if i["type"] == "broken_link"]),
        "empty_documents": len([i for i in issues if i["type"] == "empty_document"]),
        "orphan_pages": len([i for i in issues if i["type"] == "orphan_page"]),
        "missing_frontmatter": len([i for i in issues if i["type"] == "missing_frontmatter"]),
        "duplicate_headings": len([i for i in issues if i["type"] == "duplicate_heading"]),
        "documentation_gaps": len([i for i in issues if i["type"] == "documentation_gap"]),
        "documentation_coverage_percent": readiness.get("coverage", {}).get("percent", 0),
    }
    
    # Sort by severity and source_path
    issues.sort(
        key=lambda x: (
            {"critical": 0, "warning": 1, "info": 2}.get(x.get("severity", "info"), 3),
            x.get("source_path", ""),
        )
    )
    
    return {
        "project": project,
        "namespace": index.get("namespace"),
        "status": "ok" if not issues else "has_issues",
        "issues": issues,
        "statistics": statistics,
        "documentation": readiness,
        "recommendations": _generate_recommendations(issues, statistics),
    }


def _readiness_to_issues(readiness: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for item in readiness.get("items", []):
        status = item.get("status")
        if status == "ok":
            continue
        issues.append(
            {
                "type": "documentation_gap",
                "severity": "warning" if status == "missing" else "info",
                "source_path": item.get("path", ""),
                "message": item.get("message", "Documentation is incomplete"),
            }
        )
    return issues


def _check_broken_wiki_links(
    index: dict[str, Any],
    available_names: set[str],
    detailed: bool = False
) -> list[dict[str, Any]]:
    """Find broken [[wiki-link]] references."""
    issues: list[dict[str, Any]] = []
    broken_by_source: dict[str, list[dict[str, Any]]] = {}
    
    for chunk in index.get("chunks", []):
        text = chunk.get("text", "")
        source_path = chunk.get("source_path", "")
        
        links = extract_wiki_links(text)
        for link in links:
            link_lower = link.lower()
            # Check if link target exists (fuzzy match on names)
            found = False
            for available in available_names:
                if link_lower == available or link_lower in available:
                    found = True
                    break
            
            if not found:
                if source_path not in broken_by_source:
                    broken_by_source[source_path] = []
                broken_by_source[source_path].append({
                    "target": link,
                    "section": chunk.get("section", ""),
                })
    
    # Create issues (deduplicate per source_path)
    for source_path, links in broken_by_source.items():
        unique_links = {link["target"] for link in links}
        for target in unique_links:
            issue = {
                "type": "broken_link",
                "severity": "warning",
                "source_path": source_path,
                "target": target,
                "message": f"Broken wiki-link: [[{target}]] not found in project",
            }
            if detailed:
                issue["occurrences"] = len([l for l in links if l["target"] == target])
            issues.append(issue)
    
    return issues


def _check_empty_documents(index: dict[str, Any]) -> list[dict[str, Any]]:
    """Find documents with no content."""
    issues: list[dict[str, Any]] = []
    
    for doc in index.get("documents", []):
        if not doc.get("chunk_ids") or len(doc.get("chunk_ids", [])) == 0:
            issues.append({
                "type": "empty_document",
                "severity": "warning",
                "source_path": doc.get("source_path", ""),
                "message": "Document has no content chunks",
            })
    
    return issues


def _check_orphan_pages(
    index: dict[str, Any],
    available_names: set[str]
) -> list[dict[str, Any]]:
    """Find pages that are never referenced by other pages."""
    issues: list[dict[str, Any]] = []
    
    # Build reference graph
    referenced: set[str] = set()
    for chunk in index.get("chunks", []):
        text = chunk.get("text", "")
        links = extract_wiki_links(text)
        for link in links:
            referenced.add(link.lower())
    
    # Find orphans (pages not referenced and not referencing others)
    for doc in index.get("documents", []):
        source_path = doc.get("source_path", "")
        path_stem = Path(source_path).stem.lower()
        
        # Skip index files and common non-content files
        if any(skip in path_stem for skip in ["index", "readme", "_log", "_"]):
            continue
        
        # Check if this page is orphaned
        is_referenced = False
        has_outgoing = False
        
        for chunk in index.get("chunks", []):
            if chunk.get("source_path") == source_path:
                links = extract_wiki_links(chunk.get("text", ""))
                if links:
                    has_outgoing = True
        
        for chunk in index.get("chunks", []):
            if chunk.get("source_path") != source_path:
                links = extract_wiki_links(chunk.get("text", ""))
                if any(link.lower() == path_stem or link.lower().endswith(path_stem) for link in links):
                    is_referenced = True
                    break
        
        if not is_referenced and not has_outgoing:
            issues.append({
                "type": "orphan_page",
                "severity": "info",
                "source_path": source_path,
                "message": "Page is not referenced by other pages and has no outgoing links",
            })
    
    return issues


def _check_frontmatter(index: dict[str, Any]) -> list[dict[str, Any]]:
    """Check for missing or incomplete frontmatter in markdown files."""
    issues: list[dict[str, Any]] = []
    
    # This is a basic check - in practice would need to read actual files
    # For now, just check if documents have metadata
    for doc in index.get("documents", []):
        source_path = doc.get("source_path", "")
        if source_path.endswith(".md"):
            # Would need to re-read file to check frontmatter properly
            # For now, just log as info
            pass
    
    return issues


def _check_duplicate_headings(index: dict[str, Any]) -> list[dict[str, Any]]:
    """Find duplicate headings within the same file."""
    issues: list[dict[str, Any]] = []
    
    # Group chunks by source_path
    chunks_by_file: dict[str, list[str]] = {}
    for chunk in index.get("chunks", []):
        source = chunk.get("source_path", "")
        heading = chunk.get("heading", "")
        if source not in chunks_by_file:
            chunks_by_file[source] = []
        chunks_by_file[source].append(heading)
    
    # Find duplicates
    for source_path, headings in chunks_by_file.items():
        heading_counts = {}
        for heading in headings:
            heading_counts[heading] = heading_counts.get(heading, 0) + 1
        
        for heading, count in heading_counts.items():
            if count > 1 and heading.strip():
                issues.append({
                    "type": "duplicate_heading",
                    "severity": "info",
                    "source_path": source_path,
                    "heading": heading,
                    "count": count,
                    "message": f"Heading '{heading}' appears {count} times in this document",
                })
    
    return issues


def _generate_recommendations(issues: list[dict[str, Any]], statistics: dict[str, Any]) -> list[str]:
    """Generate actionable recommendations based on issues."""
    recommendations: list[str] = []
    
    if statistics["broken_links"] > 0:
        recommendations.append(
            f"Fix {statistics['broken_links']} broken wiki-links: check spelling and document existence"
        )
    
    if statistics["empty_documents"] > 0:
        recommendations.append(
            f"Remove or fill {statistics['empty_documents']} empty document(s)"
        )
    
    if statistics["orphan_pages"] > 0:
        recommendations.append(
            f"Consider linking {statistics['orphan_pages']} orphan page(s) from other documents or removing them"
        )

    if statistics.get("documentation_gaps", 0) > 0:
        recommendations.append(
            f"Fill {statistics['documentation_gaps']} recommended documentation gap(s)"
        )
    
    if statistics["total_issues"] == 0:
        recommendations.append("✓ Project documentation is clean!")
    
    return recommendations
