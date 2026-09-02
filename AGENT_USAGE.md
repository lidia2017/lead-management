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

The agent initially validated the prospect's email by relying on FastAPI's
`EmailStr` type on the form field. That **silently fails for multipart form
fields**: `Form(...)` values arrive as plain strings and Pydantic's `EmailStr`
coercion is not applied the way it is for a JSON body, so an obviously invalid
address like `not-an-email` sailed through and created a lead.

I caught it by adding a test (`test_rejects_bad_email`) that posts a malformed
address and asserts a `422` — it failed (the endpoint returned `201`). The fix
was to validate the email explicitly inside the handler with a
`TypeAdapter(EmailStr)` and raise `422` on failure. The test now passes and the
bad address is rejected. This is exactly the kind of "looks-right, is-wrong"
mistake that only surfaces with a test around the real transport (multipart vs
JSON), which is why I kept verification in my own hands.

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
