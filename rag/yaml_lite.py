from __future__ import annotations

from pathlib import Path
import re
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
    if re.fullmatch(r"[-+]?\d+", value):
        return int(value)
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

    if not lines:
        return {}

    def parse_block(index: int, indent: int) -> tuple[Any, int]:
        if index >= len(lines) or lines[index][0] != indent:
            raise ValueError(f"Unexpected indentation in {path}")
        is_list = lines[index][1].startswith("- ")
        if is_list:
            values: list[Any] = []
            while index < len(lines) and lines[index][0] == indent:
                _, text = lines[index]
                if not text.startswith("- "):
                    raise ValueError(f"Mixed YAML list and mapping in {path}: {text}")
                item_text = text[2:].strip()
                index += 1
                if not item_text:
                    if index >= len(lines) or lines[index][0] <= indent:
                        raise ValueError(f"Missing nested value in {path}: {text}")
                    value, index = parse_block(index, lines[index][0])
                    values.append(value)
                    continue
                if ":" not in item_text or item_text.startswith(('"', "'")):
                    values.append(_parse_scalar(item_text))
                    continue
                key, value_text = _split_key_value(item_text)
                item: dict[str, Any] = {key: _parse_scalar(value_text)} if value_text else {key: {}}
                while index < len(lines) and lines[index][0] > indent:
                    child_indent, child_text = lines[index]
                    if child_indent != indent + 2 or child_text.startswith("- "):
                        raise ValueError(f"Unsupported YAML indentation in {path}: {child_text}")
                    child_key, child_value = _split_key_value(child_text)
                    index += 1
                    if child_value:
                        item[child_key] = _parse_scalar(child_value)
                    elif index < len(lines) and lines[index][0] > child_indent:
                        item[child_key], index = parse_block(index, lines[index][0])
                    else:
                        item[child_key] = {}
                values.append(item)
            return values, index

        mapping: dict[str, Any] = {}
        while index < len(lines) and lines[index][0] == indent:
            _, text = lines[index]
            if text.startswith("- "):
                raise ValueError(f"Mixed YAML list and mapping in {path}: {text}")
            key, value = _split_key_value(text)
            index += 1
            if value:
                mapping[key] = _parse_scalar(value)
            elif index < len(lines) and lines[index][0] > indent:
                mapping[key], index = parse_block(index, lines[index][0])
            else:
                mapping[key] = {}
        return mapping, index

    result, end = parse_block(0, 0)
    if end != len(lines) or not isinstance(result, dict):
        raise ValueError(f"Unexpected YAML root in {path}")
    return result
