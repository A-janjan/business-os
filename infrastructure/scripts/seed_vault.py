#!/usr/bin/env python3
"""Create the Obsidian-compatible vault structure.

Safe to re-run: existing files are never overwritten.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VAULT = REPO_ROOT / "knowledge"

FOLDERS = [
    "00-SYSTEM/TEMPLATES",
    "01-CLIENTS",
    "02-PROJECTS",
    "03-OPERATIONS/SOPs",
    "03-OPERATIONS/Workflows",
    "04-CONTENT/Ideas",
    "04-CONTENT/Drafts",
    "04-CONTENT/Calendar",
    "05-FINANCES/Income",
    "05-FINANCES/Expenses",
    "05-FINANCES/Invoices",
    "06-RESEARCH/Market",
    "06-RESEARCH/Competitors",
    "07-DAILY-NOTES",
    "08-QUEUE",
    "09-GENERATED/Reports",
    "09-GENERATED/Drafts",
    "09-GENERATED/Briefings",
    "10-ARCHIVE",
]

CLAUDE_MD = """---
title: CLAUDE.md
type: system
generated: false
---

# Business OS — Operating Context

This vault is the single source of truth for business knowledge.
It is Markdown + YAML frontmatter, fully compatible with Obsidian,
and readable/editable by any text editor.

## Rules

- Human notes are never overwritten by AI without explicit approval.
- All AI-generated content lands under `09-GENERATED/`.
- Requests enter through `08-QUEUE/` as Markdown files with frontmatter.
- Every entity gets a note: clients under `01-CLIENTS/`, projects under `02-PROJECTS/`.
"""

SETTINGS_MD = """---
title: SETTINGS
type: system
generated: false
---

# Business Settings

## Identity
- Name: _(set your name)_
- Company: _(set your company)_
- Currency: USD
- Timezone: _(set your timezone)_

## Targets
- Monthly revenue target: _(set target)_
- Tasks per week: _(set target)_

## Writing style
_(Describe your tone, preferred platforms, and publishing cadence.)_
"""

TEMNA_CLIENT = """---
title: "{name}"
type: client
status: active
company: ""
tags: [client]
date: ""
---

# {name}

## Contact
- Email:
- Phone:
- Address:

## Contract
- Payment terms:
- Notes:

## History
"""

TEMNA_PROJECT = """---
title: "{name}"
type: project
status: active
client: ""
start: ""
deadline: ""
tags: [project]
---

# {name}

## Description

## Milestones
- [ ]

## Notes
"""

TEMNA_DAILY = """---
title: "Daily Note - {date}"
type: daily-note
date: "{date}"
tags: [daily-note]
---

# Daily Note - {date}

## Completed

## Tasks
- [ ]

## Meetings

## Decisions

## Income

## Expenses

## Ideas

## Blockers
"""

CLI_TEMPLATE_FILE = "TEMPLATES/client.md"
PROJ_TEMPLATE_FILE = "TEMPLATES/project.md"
DAILY_TEMPLATE_FILE = "TEMPLATES/daily-note.md"


def main() -> int:
    VAULT.mkdir(parents=True, exist_ok=True)
    created = 0
    for folder in FOLDERS:
        (VAULT / folder).mkdir(parents=True, exist_ok=True)

    def _write_once(rel: str, content: str) -> None:
        nonlocal created
        target = VAULT / rel
        if target.exists():
            return
        content = content.replace("{date}", "YYYY-MM-DD").replace("{name}", "Example")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        created += 1

    _write_once("00-SYSTEM/CLAUDE.md", CLAUDE_MD)
    _write_once("00-SYSTEM/SETTINGS.md", SETTINGS_MD)
    _write_once("00-SYSTEM/TEMPLATES/client.md", TEMNA_CLIENT)
    _write_once("00-SYSTEM/TEMPLATES/project.md", TEMNA_PROJECT)
    _write_once("00-SYSTEM/TEMPLATES/daily-note.md", TEMNA_DAILY)

    print(f"Vault ready at {VAULT} ({created} new files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
