"""Knowledge base routes: list/search/read/write/archive + daily notes."""
from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user, log_activity
from ..knowledge.repository import (
    Repository,
    KnowledgeError,
    extract_daily_sections,
    extract_finance_lines,
)
from ..securityutil import PathSafetyError, today_str
from ..models import User

router = APIRouter(prefix="/knowledge", tags=["knowledge"])
notes_router = APIRouter(prefix="/notes", tags=["notes"])


def _repo() -> Repository:
    return Repository(get_settings().knowledge_dir)


def _guard(exc: Exception) -> HTTPException:
    if isinstance(exc, PathSafetyError):
        return HTTPException(status_code=400, detail="invalid path")
    if isinstance(exc, KnowledgeError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=500, detail="knowledge repository error")


@router.get("/structure")
def structure(_: User = Depends(get_current_user)):
    try:
        return _repo().structure()
    except Exception as exc:  # noqa: BLE001
        raise _guard(exc)


@router.get("/notes")
def list_notes(
    q: str = "",
    folder: str = "",
    tag: str = "",
    _: User = Depends(get_current_user),
):
    repo = _repo()
    if q or tag:
        notes = repo.search(q, folder=folder, tag=tag)
    else:
        notes = repo.all_notes()
        if folder:
            notes = [n for n in notes if n["folder"] == folder]
        if tag:
            notes = [n for n in notes if tag in n["tags"]]
    return {"items": notes, "total": len(notes)}


@router.post("/notes", status_code=201)
def create_note(payload: dict, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    repo = _repo()
    try:
        rel = str(payload.get("path", ""))
        fm = payload.get("frontmatter", {})
        body = str(payload.get("body", ""))
        note = repo.create(rel, fm, body)
        log_activity(db, "user", "knowledge.created", "knowledge", note["path"], f"Added note {note['title']}")
        db.commit()
        return note
    except Exception as exc:
        raise _guard(exc)


@router.get("/note")
def get_note(path: str = Query(...), _: User = Depends(get_current_user)):
    repo = _repo()
    try:
        return repo.read(path)
    except Exception as exc:
        raise _guard(exc)


@router.patch("/note")
def update_note(payload: dict, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    repo = _repo()
    try:
        note = repo.update(
            str(payload.get("path", "")),
            payload.get("frontmatter") if "frontmatter" in payload else None,
            payload.get("body") if "body" in payload else None,
        )
        log_activity(db, "user", "knowledge.updated", "knowledge", note["path"], f"Updated note {note['title']}")
        db.commit()
        return note
    except Exception as exc:
        raise _guard(exc)


@router.post("/note/archive")
def archive_note(payload: dict, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    repo = _repo()
    try:
        result = repo.archive(str(payload.get("path", "")))
        log_activity(db, "user", "knowledge.archived", "knowledge", "", f"Archived note {result.get('archived_to')}")
        db.commit()
        return result
    except Exception as exc:
        raise _guard(exc)


@router.get("/backlinks")
def backlinks(path: str = Query(...), _: User = Depends(get_current_user)):
    repo = _repo()
    try:
        return {"backlinks": repo.backlinks(path)}
    except Exception as exc:
        raise _guard(exc)


# ---- daily notes ----
@notes_router.get("/")
def list_daily_notes(
    start: str = "",
    end: str = "",
    _: User = Depends(get_current_user),
):
    repo = _repo()
    notes = [n for n in repo.all_notes() if n["is_daily_note"]]
    if start:
        notes = [n for n in notes if str(n["frontmatter"].get("date", "")) >= start]
    if end:
        notes = [n for n in notes if str(n["frontmatter"].get("date", "")) <= end]
    notes.sort(key=lambda n: str(n["frontmatter"].get("date", "")), reverse=True)
    return {"items": notes, "total": len(notes)}


@notes_router.get("/{note_date}")
def get_daily_note(note_date: str, _: User = Depends(get_current_user)):
    """note_date: YYYY-MM-DD. Returns the extracted sections and finance lines."""
    repo = _repo()
    notes = [n for n in repo.all_notes() if str(n["frontmatter"].get("date", "")) == note_date]
    if not notes:
        raise HTTPException(status_code=404, detail="daily note not found")
    note_path = notes[0]["path"]
    note = repo.read(note_path)
    raw = (repo.base / note_path).read_text(encoding="utf-8", errors="replace")
    sections = extract_daily_sections(raw)
    finances = extract_finance_lines(sections)
    return {"path": note["path"], "title": note["title"], "body": note["body"],
            "sections": sections, "finance_lines": finances}


@notes_router.put("/{note_date}")
def upsert_daily_note(note_date: str, payload: dict, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    repo = _repo()
    try:
        date_str = note_date
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
    rel = f"07-DAILY-NOTES/{date_str}-daily.md"
    body = str(payload.get("body", ""))
    title = str(payload.get("title") or f"Daily Note - {date_str}")
    frontmatter = {"title": title, "date": date_str, "daily_note": True, "tags": ["daily-note"]}
    try:
        existing = repo.read(rel)
        note = repo.update(rel, frontmatter, body)
        action = "updated"
    except KnowledgeError:
        note = repo.create(rel, frontmatter, body)
        action = "created"
    log_activity(db, "user", f"daily_note.{action}", "note", note["path"], f"Daily note {action}: {date_str}")
    db.commit()
    return note
