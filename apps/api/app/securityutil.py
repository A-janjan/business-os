"""Security primitives: path safety, frontmatter parsing, link extraction."""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import yaml

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
_WIKI_LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
_MD_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


class PathSafetyError(ValueError):
    """Raised when a requested path resolves outside the vault."""


def resolve_vault_path(base: Path, rel: str) -> Path:
    """Resolve `rel` inside `base`, refusing traversal and absolute escapes."""
    if not rel:
        raise PathSafetyError("empty path")
    if "\x00" in rel:
        raise PathSafetyError("NUL byte in path")
    base_r = base.resolve()
    candidate = (base_r / rel).resolve()
    if candidate != base_r and base_r not in candidate.parents:
        raise PathSafetyError(f"path escapes vault: {rel}")
    return candidate


def rel_vault_path(base: Path, path: Path) -> str:
    return path.resolve().relative_to(base.resolve()).as_posix()


def split_frontmatter(text: str) -> tuple[dict, str]:
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    try:
        data = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}, text
    if not isinstance(data, dict):
        return {}, text
    return data, text[match.end():]


def split_frontmatter_or_default(text: str, title: str) -> tuple[dict, str]:
    return split_frontmatter(text)


def serialize_note(frontmatter: dict, body: str) -> str:
    if not frontmatter:
        return body.lstrip("\n")
    fm = yaml.safe_dump(
        frontmatter,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        width=1024,
    )
    return f"---\n{fm}---\n\n{body.lstrip('\n')}"


def extract_title(text: str, fallback: str) -> str:
    _, body = split_frontmatter(text)
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
        if stripped:
            return stripped[:300]
    return fallback


def extract_links(text: str) -> list[str]:
    """Return wiki-style `[[targets]]` referenced by the note."""
    _, body = split_frontmatter(text)
    return sorted({m.group(1).strip() for m in _WIKI_LINK_RE.finditer(body)})


def extract_markdown_links(text: str) -> list[str]:
    _, body = split_frontmatter(text)
    return sorted({m.group(1).strip() for m in _MD_LINK_RE.finditer(body)})


def normalize_rel_path(rel: str) -> str:
    """Normalize a relative path (no leading './', no duplicate separators)."""
    p = Path(rel)
    parts = []
    for part in p.parts:
        if part in (".", ""):
            continue
        if part == "..":
            if parts:
                parts.pop()
            else:
                raise PathSafetyError("path escapes vault")
            continue
        parts.append(part)
    normalized = "/".join(parts)
    if not normalized:
        raise PathSafetyError("empty path")
    return normalized


def today_str() -> str:
    return date.today().isoformat()


def clamp_str(value: str, limit: int) -> str:
    return (value or "")[:limit]
