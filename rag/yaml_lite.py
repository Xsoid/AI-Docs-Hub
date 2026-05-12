from __future__ import annotations

from pathlib import Path
from typing import Any


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a small YAML file.

    PyYAML is used when installed. The fallback parser supports the restricted
    config shape used by configs/projects/*.yaml: top-level scalars and lists of
    scalars or dictionaries.
    """

    try:
        import yaml  # type: ignore

        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            raise ValueError(f"{path} must contain a YAML mapping")
        return data
    except ModuleNotFoundError:
        return _load_restricted_yaml(path)


def _strip_comment(line: str) -> str:
    in_single = False
    in_double = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return line[:i]
    return line


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if value == "":
        return ""
    if value in {"null", "Null", "NULL", "~"}:
        return None
    if value in {"true", "True", "TRUE"}:
        return True
    if value in {"false", "False", "FALSE"}:
        return False
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def _split_key_value(text: str) -> tuple[str, str]:
    if ":" not in text:
        raise ValueError(f"Expected key/value line, got: {text}")
    key, value = text.split(":", 1)
    return key.strip(), value.strip()


def _load_restricted_yaml(path: Path) -> dict[str, Any]:
    raw_lines = path.read_text(encoding="utf-8").splitlines()
    lines: list[tuple[int, str]] = []
    for raw in raw_lines:
        clean = _strip_comment(raw).rstrip()
        if not clean.strip():
            continue
        indent = len(clean) - len(clean.lstrip(" "))
        lines.append((indent, clean.strip()))

    result: dict[str, Any] = {}
    i = 0
    while i < len(lines):
        indent, text = lines[i]
        if indent != 0:
            raise ValueError(f"Unexpected indentation in {path}: {text}")
        key, value = _split_key_value(text)
        if value:
            result[key] = _parse_scalar(value)
            i += 1
            continue

        i += 1
        items: list[Any] = []
        mapping: dict[str, Any] = {}
        mode: str | None = None

        while i < len(lines) and lines[i][0] > indent:
            child_indent, child_text = lines[i]
            if child_indent == 2 and child_text.startswith("- "):
                mode = "list"
                item_text = child_text[2:].strip()
                if ":" in item_text and not item_text.startswith(('"', "'")):
                    item: dict[str, Any] = {}
                    item_key, item_value = _split_key_value(item_text)
                    item[item_key] = _parse_scalar(item_value)
                    i += 1
                    while i < len(lines) and lines[i][0] >= 4:
                        _, nested_text = lines[i]
                        nested_key, nested_value = _split_key_value(nested_text)
                        item[nested_key] = _parse_scalar(nested_value)
                        i += 1
                    items.append(item)
                else:
                    items.append(_parse_scalar(item_text))
                    i += 1
            elif child_indent == 2:
                mode = "mapping"
                child_key, child_value = _split_key_value(child_text)
                mapping[child_key] = _parse_scalar(child_value)
                i += 1
            else:
                raise ValueError(f"Unsupported YAML indentation in {path}: {child_text}")

        result[key] = items if mode == "list" else mapping

    return result

