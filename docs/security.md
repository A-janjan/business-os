# Security Model

## Authentication & authorization

- Registration is **bootstrap-only**: the first user becomes admin; after that,
  registration returns 403 unless `ADMIN_BOOTSTRAP=true` (dev only).
- Passwords are hashed with **argon2** (`argon2-cffi`, argon2id).
- Tokens are **JWT HS256**, signed with `AUTH_SECRET`, expiring after
  `ACCESS_TOKEN_EXPIRE_MINUTES` (24h default).
- All endpoints except `/api/health`, `/api/auth/login`, `/api/auth/register`
  require a valid Bearer token. Frontend stores the token in `localStorage`
  and attaches it via the API client.

## AI safety

- The AI is treated as an **untrusted text generator**. Every agent output is
  validated against a pydantic schema before it is displayed or persisted.
- Prompts never include secrets; context is built from a curated grounding
  bundle, not raw filesystem content.
- **No arbitrary shell execution**, no tool execution, no credential use.
- **No fabricated output**: if the provider is unconfigured, every AI endpoint
  returns `503` with an explicit message. No fallback fakes.
- **Approval-gated consequential actions**: content drafts wait in
  `approval_requests` before being saved as content items. Publishing, sending,
  deleting, and external writes are not implemented in this build and require
  explicit human action.
- Output logging never includes secrets or raw credential material.

## Data protection

- `.env` is gitignored; no API keys or tokens are ever committed.
- Path safety: the knowledge repository resolves every path against the vault
  root and refuses NUL bytes, absolute paths, and `..` traversal
  (`resolve_vault_path`).
- SQL access is via SQLAlchemy ORM (prepared statements) — no string-built
  queries.
- Pydantic validation on every API input (`ClientIn`, `ProjectIn`, `TaskIn`,
  ...) with explicit schemas and length caps.
- Soft deletes only (`status="archived"/"churned"/"void"`); no hard deletes in
  any normal path.

## File handling

- The vault is plain Markdown with YAML frontmatter parsed by `yaml.safe_load`.
- Notes are created with a unique path; duplicates are rejected.
- Frontend renders Markdown as plain text (no `dangerouslySetInnerHTML`).

## Prompt injection

- Untrusted content (notes, external research, queue descriptions) is treated
  as data, never as instructions. Agent prompts clearly separate "context"
  from "instructions".
- Tool allowlists are enforced by omitting tool-calling entirely in this build
  (the executor only performs LLM calls + validated side effects).

## Secrets hygiene

- `auth_secret` documented to be strong (≥ 32 bytes); `.env.example` documents
  the variables and their purpose.
- n8n webhook URLs are operator-configured; no third-party services receive
  tokens by default.

## Known gaps (honest)

- No refresh tokens (24h access tokens, single-user app).
- No rate limiting at the application layer (put a reverse proxy / rate limiter
  in front for production).
- No audit log for approval side effects (activity logs record them; a SIEM
  pipeline is future scope).
- Frontend is not XSS-hardened beyond React's defaults for an admin tool.
