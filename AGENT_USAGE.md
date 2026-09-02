# Coding-agent usage writeup

## Tools used

- **Claude Code** (Opus 4.8) as the primary coding agent — used to scaffold the
  entire repo, write the FastAPI backend, the Next.js frontend, Docker setup,
  tests, and docs, driven from an interactive session.

## What I delegated vs. wrote myself

**Delegated to the agent (majority of the code):**
- Backend scaffolding: FastAPI app, SQLModel models, routes, JWT auth,
  pluggable email service, file-storage abstraction, and the pytest suite.
- Frontend: the three pages (public form, login, dashboard), the typed API
  client, and styling.
- Infra & docs: `docker-compose.yml`, Dockerfiles, README/RUNNING/SYSTEM_DESIGN.

**Directed / decided myself (the "what" and the guardrails):**
- The architecture and the key trade-offs — Postgres + local file volume,
  pluggable email with a dev-safe default, JWT with a seeded attorney,
  server-side state-machine enforcement. I made these calls up front and had
  the agent implement to them.
- The state-transition rules (only `PENDING → REACHED_OUT`, everything else is
  `409`) and where they live (service layer, not the route handler).
- Reviewing every file, running the test suite, and validating the build.

I let the agent own boilerplate and mechanical wiring where a mistake is cheap
and caught by tests/typecheck, and kept design decisions and verification for
myself.

## One place the agent produced wrong / subtly bad code — and the fix

**Example A — multipart email validation.** The agent initially validated the
prospect's email by relying on FastAPI's `EmailStr` type on the form field.
That **silently fails for multipart form fields**: `Form(...)` values arrive as
plain strings and Pydantic's `EmailStr` coercion is not applied the way it is
for a JSON body, so an invalid address like `not-an-email` sailed through. I
caught it with a test (`test_rejects_bad_email`) asserting `422`; it returned
`201`. Fix: validate explicitly inside the handler with `TypeAdapter(EmailStr)`.

**Example B — rate-limiter decorator broke the app (caught at import time).**
When adding scalability, the agent wired the `slowapi` `@limiter.limit(...)`
decorator onto the public submit route. Because that route uses
`from __future__ import annotations` **and** an `UploadFile` multipart param,
slowapi's wrapper couldn't resolve the now-stringified annotations in its own
module globals — FastAPI blew up at import with a confusing "Invalid args for
response field! ForwardRef('UploadFile')". The whole test suite failed to even
collect. I diagnosed the annotation/wrapper interaction, dropped slowapi
entirely, and reimplemented rate limiting as a small Redis fixed-window
**FastAPI dependency** — fewer deps, no annotation pitfall, still shared across
replicas. Tests went back to green (12 passing).

Both are classic "looks-right, is-wrong" agent outputs — one silent, one loud —
which is why I kept the test suite and every run in my own hands.

## Prompt-log excerpts

See `NOTES.md` for per-file attribution. Representative prompts from the
session:

> "Build a full-stack lead-management app: FastAPI + Next.js, Postgres + local
> file storage for resumes, pluggable email (console/SMTP/SendGrid) sent in a
> background task, JWT auth with a seeded attorney. Public form creates a
> PENDING lead and emails prospect + attorney; internal UI lists leads and
> marks them REACHED_OUT. Structure it like a production repo."

> "Enforce the state machine in the service layer — only PENDING→REACHED_OUT is
> valid, reject anything else with 409. Add pytest coverage for the illegal
> transition."

> "Write a pytest suite that runs without Postgres (SQLite + temp upload dir)
> and covers: public submit → PENDING, bad email → 422, unsupported file → 400,
> list requires auth, state transition + illegal transition, resume download
> requires auth."
