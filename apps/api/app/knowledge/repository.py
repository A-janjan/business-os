"""Markdown knowledge repository (Obsidian-compatible vault).

The vault is plain files: Markdown + YAML frontmatter, no Obsidian-specific
APIs. This module is the ONLY code allowed to touch the vault, and it refuses
to escape the vault root.
"""
from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from ..securityutil import (
    PathSafetyError,
    clamp_str,
    extract_links,
    extract_title,
    normalize_rel_path,
    resolve_vault_path,
    rel_vault_path,
    serialize_note,
    split_frontmatter,
)

NOTE_SUFFIX = ".md"
SYSTEM_FOLDERS = (
    "00-SYSTEM", "01-CLIENTS", "02-PROJECTS", "03-OPERATIONS", "04-CONTENT",
    "05-FINANCES", "06-RESEARCH", "07-DAILY-NOTES", "08-QUEUE", "09-GENERATED", "10-ARCHIVE",
)


class KnowledgeError(Exception):
    pass


class Repository:
    def __init__(self, base: Path):
        self.base = base

    # -- discovery ------------------------------------------------------
    def all_notes(self) -> list[dict[str, Any]]:
        """List all markdown notes with lightweight metadata."""
        notes: list[dict[str, Any]] = []
        if not self.base.exists():
            return notes
        for path in sorted(self.base.rglob("*.md")):
            try:
                rel = rel_vault_path(self.base, path)
            except Exception:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            fm, body = split_frontmatter(text)
            notes.append({
                "path": rel,
                "title": str(fm.get("title") or extract_title(text, Path(rel).stem)),
                "folder": str(fm.get("folder") or (rel.split("/")[0] if "/" in rel else "")),
                "tags": fm.get("tags") if isinstance(fm.get("tags"), list) else [],
                "frontmatter": fm,
                "updated_at": path.stat().st_mtime,
                "size": path.stat().st_size,
                "is_daily_note": bool(fm.get("daily_note")) or rel.startswith("07-DAILY-NOTES/"),
            })
        return notes

    def structure(self) -> dict[str, Any]:
        tree: dict[str, Any] = {"folders": [], "notes": []}
        if self.base.exists():
            for path in self.base.iterdir():
                if path.is_dir():
                    tree["folders"].append({
                        "name": path.name,
                        "count": sum(1 for _ in path.rglob("*.md")),
                    })
        tree["folders"].sort(key=lambda f: f["name"])
        tree["notes_total"] = len(self.all_notes())
        return tree

    # -- read ----------------------------------------------------------
    def read(self, rel: str) -> dict[str, Any]:
        path = resolve_vault_path(self.base, normalize_rel_path(rel))
        if not path.exists() or not path.is_file():
            raise KnowledgeError("note not found")
        text = path.read_text(encoding="utf-8", errors="replace")
        fm, body = split_frontmatter(text)
        return {
            "path": rel_vault_path(self.base, path),
            "title": str(fm.get("title") or extract_title(text, path.stem)),
            "body": body,
            "frontmatter": fm,
            "links": extract_links(text),
            "updated_at": path.stat().st_mtime,
            "size": path.stat().st_size,
        }

    def search(self, query: str, folder: str = "", tag: str = "") -> list[dict[str, Any]]:
        q = query.strip().lower()
        results = []
        for note in self.all_notes():
            if folder and note["folder"] != folder:
                continue
            if tag and tag not in note["tags"]:
                continue
            hay = (note["title"] + " " + " ".join(note["tags"]) + " " + note["frontmatter"].get("type", "")).lower()
            body_hit = False
            try:
                body_text = (self.base / note["path"]).read_text(encoding="utf-8", errors="replace").lower()
                body_hit = q in body_text
            except Exception:
                body_hit = False
            if q in hay or body_hit:
                results.append({**note, "body_match": body_hit})
        return results

    def backlinks(self, target_path: str) -> list[str]:
        """Which notes link to `target_path`? Matches wiki-style targets and markdown links."""
        target = normalize_rel_path(target_path).replace(".md", "").lower()
        target_stem = target.rsplit("/", 1)[-1]
        backlinked: list[str] = []
        for note in self.all_notes():
            if note["path"] == target_path:
                continue
            text = (self.base / note["path"]).read_text(encoding="utf-8", errors="replace")
            links = extract_links(text)
            for link in links:
                link_n = link.replace(".md", "").lower()
                if (
                    link_n == target
                    or link_n.endswith("/" + target_stem)
                    or link_n == target_stem
                    or target_stem in link_n
                ):
                    backlinked.append(note["path"])
                    break
        return sorted(set(backlinked))

    # -- write ---------------------------------------------------------
    def create(self, path: str, frontmatter: dict, body: str) -> dict[str, Any]:
        rel = normalize_rel_path(path)
        if not rel.endswith(NOTE_SUFFIX):
            rel += NOTE_SUFFIX
        target = resolve_vault_path(self.base, rel)
        if target.exists():
            raise KnowledgeError("file already exists")
        target.parent.mkdir(parents=True, exist_ok=True)
        fm = {k: v for k, v in (frontmatter or {}).items() if v not in (None, "", [], {})}
        if "tags" not in fm:
            fm["tags"] = []
        if "date" not in fm:
            fm["date"] = datetime.now().strftime("%Y-%m-%d")
        target.write_text(serialize_note(fm, body), encoding="utf-8")
        return self.read(rel)

    def update(self, path: str, frontmatter: dict | None, body: str | None) -> dict[str, Any]:
        rel = normalize_rel_path(path)
        path_abs = resolve_vault_path(self.base, rel)
        if not path_abs.exists():
            raise KnowledgeError("note not found")
        text = path_abs.read_text(encoding="utf-8", errors="replace")
        fm_old, _ = split_frontmatter(text)
        new_fm = dict(fm_old)
        if frontmatter is not None:
            new_fm.update({k: v for k, v in frontmatter.items() if v is not None})
        new_body = body if body is not None else split_frontmatter(text)[1]
        path_abs.write_text(serialize_note(new_fm, new_body), encoding="utf-8")
        return self.read(rel)

    def archive(self, path: str) -> dict[str, Any]:
        rel = normalize_rel_path(path)
        src = resolve_vault_path(self.base, rel)
        if not src.exists():
            raise KnowledgeError("note not found")
        dest = resolve_vault_path(self.base, f"10-ARCHIVE/{Path(rel).name}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            stem = dest.stem
            i = 2
            while (dest.parent / f"{stem}-{i}.md").exists():
                i += 1
            dest = dest.parent / f"{stem}-{i}.md"
        shutil.move(str(src), str(dest))
        return {"archived_to": rel_vault_path(self.base, dest)}

    # -- index maintenance ----------------------------------------------
    def sync(self) -> int:
        """Return how many markdown files it found (used by the sync endpoint)."""
        return len(self.all_notes())


_DAY_SECTION_RE = re.compile(r"^##\s*(?P<name>[^\n]+)\s*$", re.MULTILINE)


def extract_daily_sections(text: str) -> dict[str, list[str]]:
    """Deterministically extract sections from a daily note.

    Completed/Blockers/Tasks/Income/Expenses/Decisions become structured
    entries; nothing is removed from the original text.
    """
    _, body = split_frontmatter(text)
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in body.splitlines():
        header = _DAY_SECTION_RE.match(line)
        if header:
            current = header.group("name").strip().lower()
            sections[current] = []
            continue
        if current and line.strip():
            sections[current].append(line.strip())
    return sections


def extract_finance_lines(sections: dict[str, list[str]]) -> list[dict[str, Any]]:
    """Pull 'RECEIVED: 500 USD - Client A' style lines into structured dicts."""
    items = []
    for section, entries in sections.items():
        if "income" not in section and "revenue" not in section:
            continue
        for entry in entries:
            m = re.search(r"RECEIVED:\s*(?P<amount>[\d,.]+)?\s*(?P<currency>[A-Z]{3})?\s*[-–—]\s*(?P<client>.*)", entry, re.IGNORECASE)
            if m:
                amount = m.group("amount")
                amount = amount.replace(",", "") if amount else ""
                items.append({"kind": "income", "amount": float(amount) if amount else None,
                              "currency": (m.group("currency") or "USD").upper(),
                              "client": m.group("client").strip()})
    return items
