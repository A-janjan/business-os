# Knowledge Management

The knowledge layer is the central memory of Business OS. It is the one part of
the app that touches the filesystem, and it does so through a single repository
(`app/knowledge/repository.py`).

## Vault structure

```
knowledge/
├── 00-SYSTEM/          OS-level notes: CLAUDE.md, SETTINGS.md, TEMPLATES/
├── 01-CLIENTS/         one note per client
├── 02-PROJECTS/        one note per project
├── 03-OPERATIONS/      SOPs, work flows
├── 04-CONTENT/         ideas, drafts, calendar
├── 05-FINANCES/        income, expenses, invoices
├── 06-RESEARCH/        market, competitors
├── 07-DAILY-NOTES/     one note per day: YYYY-MM-DD-daily.md
├── 08-QUEUE/           pending AI requests (Markdown files)
├── 09-GENERATED/       AI-generated artifacts (never overwrite human notes)
└── 10-ARCHIVE/         archived notes
```

Paths are relative to the vault root (`KNOWLEDGE_DIR`, default `knowledge/`).
`.env` cannot safely write outside `knowledge/` — the repository validates every
path (`resolve_vault_path`) and refuses traversal, NUL bytes, and absolute paths
outside the vault.

## Markdown + YAML frontmatter

Notes use YAML frontmatter for metadata and the body for content:

```markdown
---
title: Acme Logistics
type: client
status: active
company: Acme Inc
tags: [client, active]
date: 2026-11-22
---

# Acme Logistics

## Contact
- Email: jane@acme.example.com
```

Frontmatter is parsed with `yaml.safe_load` (never `eval`); unknown/malformed
frontmatter degrades gracefully to an empty map with the body preserved.

## Operations

| Operation | Endpoint |
|---|---|
| List / search | `GET /api/knowledge/notes?q=&folder=&tag=` |
| Read | `GET /api/knowledge/note?path=` |
| Create | `POST /api/knowledge/notes` |
| Update | `PATCH /api/knowledge/note` |
| Archive | `POST /api/knowledge/note/archive` |
| Backlinks | `GET /api/knowledge/backlinks?path=` |
| Structure | `GET /api/knowledge/structure` |

Backlinks match wiki-style `[[Note-Name]]` references and match `.md` suffix
variants.

## Obsidian compatibility

The vault opens directly in Obsidian — no plugin required. Relationships work
with any `[[wiki-link]]` syntax; frontmatter supports tags, dates, and custom
metadata. Editing in Obsidian updates the underlying files, so the API reflects
changes on next read.

## Daily notes + structured extraction

`PUT /api/notes/{YYYY-MM-DD}` creates or updates `07-DAILY-NOTES/YYYY-MM-DD-daily.md`.
`GET /api/notes/{YYYY-MM-DD}` returns the note plus **deterministic** extraction:

- Sectioned extraction (`## Completed`, `## Tasks`, `## Income`, …) — raw lines, unmodified original.
- Finance line extraction — lines like `RECEIVED: 500 USD - Client A` become `{kind, amount, currency, client}` dicts. Nothing is ever removed or rewritten.

## Safety rules

- The repository is the ONLY code that reads/writes the vault.
- AI output lands in `09-GENERATED/`; the repository never overwrites existing
  human notes silently.
- Archived notes move to `10-ARCHIVE/` (never deleted, never overwritten).
- The frontend renders Markdown as plain text (no `dangerouslySetInnerHTML`).

## Queue-based requests

`08-QUEUE/` is the Markdown-file entry point for pending AI requests. The API
offers an equivalent programmatic path (`POST /api/queue/`), with the same
lifecycle. A scheduled watcher for the queue folder is **planned**; users can
start the queue with `POST /api/queue/` today.
