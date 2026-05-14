from __future__ import annotations

import re
from pathlib import Path
from typing import Any


WIKI_LINK_PATTERN = re.compile(r"\[\[([^\]]+)\]\]")
FENCE_PATTERN = re.compile(r"^ {0,3}(`{3,}|~{3,})")


def strip_markdown_code(text: str) -> str:
    """Return Markdown text with fenced and inline code masked out."""
    lines: list[str] = []
    in_fence = False
    fence_char = ""
    fence_len = 0

    for line in text.splitlines(keepends=True):
        body = line.rstrip("\n\r")
        newline = line[len(body):]
        fence_match = FENCE_PATTERN.match(body)

        if in_fence:
            lines.append(newline)
            if fence_match and fence_match.group(1).startswith(fence_char * fence_len):
                in_fence = False
                fence_char = ""
                fence_len = 0
            continue

        if fence_match:
            marker = fence_match.group(1)
            in_fence = True
            fence_char = marker[0]
            fence_len = len(marker)
            lines.append(newline)
            continue

        lines.append(_mask_inline_code(body) + newline)

    return "".join(lines)


def _mask_inline_code(line: str) -> str:
    chars = list(line)
    index = 0
    while index < len(chars):
        if chars[index] != "`":
            index += 1
            continue

        tick_count = 1
        while index + tick_count < len(chars) and chars[index + tick_count] == "`":
            tick_count += 1

        marker = "`" * tick_count
        end = line.find(marker, index + tick_count)
        if end == -1:
            index += tick_count
            continue

        for pos in range(index, end + tick_count):
            chars[pos] = " "
        index = end + tick_count

    return "".join(chars)


def extract_wiki_links(text: str) -> list[str]:
    """Extract all wiki-link references from markdown text.
    
    Args:
        text: Markdown content
    
    Returns:
        List of wiki-link targets (e.g., ['entity/person/karpathy', 'concept/rl'])
    """
    matches = WIKI_LINK_PATTERN.findall(strip_markdown_code(text))
    # Normalize: remove anchors (#section), keep only the reference part
    links = []
    for match in matches:
        # Format: [[path/to/page#section|Display Text]] -> extract 'path/to/page'
        ref = match.split("|")[0].strip().split("#")[0].strip()
        if ref:
            links.append(ref)
    return links


def find_wiki_link_references(document_path: str, text: str) -> list[dict[str, Any]]:
    """Find all wiki-link references in a document.
    
    Args:
        document_path: Source path in index (e.g., 'docs/architecture.md')
        text: Document content
    
    Returns:
        List of reference dicts with source, target, line number
    """
    references: list[dict[str, Any]] = []
    masked_text = strip_markdown_code(text)
    for line_num, (masked_line, original_line) in enumerate(
        zip(masked_text.splitlines(), text.splitlines()),
        1,
    ):
        for match in WIKI_LINK_PATTERN.finditer(masked_line):
            target = match.group(1).split("|")[0].strip().split("#")[0].strip()
            if target:
                references.append({
                    "source_path": document_path,
                    "source_line": line_num,
                    "target_ref": target,
                    "line_content": original_line.strip()[:100],  # Keep first 100 chars for context
                })
    return references


def validate_wiki_link_target(target: str, available_paths: set[str]) -> tuple[bool, str | None]:
    """Check if a wiki-link target exists in available documents.
    
    Args:
        target: Wiki-link target (e.g., 'entity/person/karpathy')
        available_paths: Set of document paths in index
    
    Returns:
        (is_valid, error_message_or_none)
    """
    # Normalize path separators
    normalized = target.lower().replace("_", "-")
    
    # Check exact match or with .md extension
    for path in available_paths:
        path_normalized = path.lower().replace("_", "-").replace(".md", "")
        if normalized == path_normalized or normalized in path_normalized:
            return True, None
    
    return False, f"Target '{target}' not found in project"


def transform_wiki_links(
    text: str, 
    available_paths: set[str], 
    format: str = "markdown"
) -> tuple[str, list[dict[str, Any]]]:
    """Transform wiki-links in markdown text.
    
    Args:
        text: Source markdown
        available_paths: Set of available document paths
        format: Output format ('markdown', 'html', 'validate')
    
    Returns:
        (transformed_text, validation_results)
    """
    validation_results: list[dict[str, Any]] = []
    
    def replace_link(match: re.Match) -> str:
        link_text = match.group(1)
        # Parse link format: [[target|display]] or [[target]]
        parts = link_text.split("|")
        target = parts[0].strip()
        display = parts[1].strip() if len(parts) > 1 else target
        
        # Validate
        is_valid, error = validate_wiki_link_target(target, available_paths)
        validation_results.append({
            "target": target,
            "display": display,
            "valid": is_valid,
            "error": error,
        })
        
        if format == "validate":
            return match.group(0)  # Return unchanged
        elif format == "html":
            if is_valid:
                href = f"/{target.lower()}.html"
                return f'<a href="{href}">{display}</a>'
            else:
                return f'<span class="broken-link">{display}</span>'
        else:  # markdown (default)
            return match.group(0)  # Keep wiki-link format
    
    transformed = WIKI_LINK_PATTERN.sub(replace_link, text)
    return transformed, validation_results
