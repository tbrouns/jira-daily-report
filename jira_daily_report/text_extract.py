from __future__ import annotations

from typing import Any


def adf_to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if not isinstance(value, dict):
        return str(value)

    parts: list[str] = []
    _walk_adf(value, parts)
    text = "".join(parts)

    # Normalize over-spaced output from rich document blocks.
    lines = [line.rstrip() for line in text.splitlines()]
    normalized: list[str] = []
    previous_blank = False
    for line in lines:
        is_blank = line == ""
        if is_blank and previous_blank:
            continue
        normalized.append(line)
        previous_blank = is_blank
    return "\n".join(normalized).strip()


def _walk_adf(node: dict[str, Any], out: list[str]) -> None:
    node_type = node.get("type")

    if node_type == "text":
        out.append(node.get("text", ""))
        return
    if node_type in {"paragraph", "heading", "blockquote"}:
        _walk_children(node, out)
        out.append("\n\n")
        return
    if node_type in {"bulletList", "orderedList"}:
        _walk_children(node, out)
        out.append("\n")
        return
    if node_type == "listItem":
        out.append("- ")
        _walk_children(node, out)
        out.append("\n")
        return
    if node_type in {"hardBreak", "rule"}:
        out.append("\n")
        return
    if node_type == "mention":
        attrs = node.get("attrs", {})
        out.append(attrs.get("text") or attrs.get("id") or "")
        return
    if node_type == "emoji":
        attrs = node.get("attrs", {})
        out.append(attrs.get("shortName") or "")
        return

    _walk_children(node, out)


def _walk_children(node: dict[str, Any], out: list[str]) -> None:
    for child in node.get("content", []) or []:
        if isinstance(child, dict):
            _walk_adf(child, out)
