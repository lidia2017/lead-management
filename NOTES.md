# Attribution notes — agent-generated vs. hand-written

This project was built with heavy use of a coding agent (**Claude Code**,
Opus 4.8). This file records provenance honestly, as requested.

## Summary

- **Design & direction:** human. Architecture, tech choices, the state-machine
  rules, the test matrix, and acceptance criteria were specified by me and the
  agent implemented against them.
- **Code:** the large majority was **agent-generated** from my prompts, then
  reviewed by me. I ran the test suite and the frontend build to validate.

## Per-area attribution

| Area                                   | Author            | Notes                                        |
|----------------------------------------|-------------------|----------------------------------------------|
| `SYSTEM_DESIGN.md` structure & choices | human-directed    | Decisions mine; prose drafted by agent.      |
| `backend/app/models.py`, `schemas.py`  | agent-generated   | Reviewed.                                    |
| `backend/app/core/*`                   | agent-generated   | Reviewed.                                    |
| `backend/app/services/*`               | agent-generated   | State-machine rules specified by me.         |
| `backend/app/api/*`                    | agent-generated   | Email-validation fix directed by me (below). |
| `backend/tests/*`                      | agent-generated   | Test cases specified by me.                  |
| `frontend/**`                          | agent-generated   | Reviewed; UX flow specified by me.           |
| `docker-compose.yml`, Dockerfiles      | agent-generated   | Reviewed.                                    |
| Docs (`README`, `RUNNING`, this file)  | agent-generated   | Reviewed & edited.                           |

## Human corrections applied

- **Multipart email validation.** Relying on `EmailStr` on a `Form(...)` field
  does not validate multipart string fields; the handler now validates the
  email explicitly with `TypeAdapter(EmailStr)` and returns `422`. Covered by
  `test_rejects_bad_email`. (See `AGENT_USAGE.md` for the full story.)
- **State transitions moved to the service layer** so the rule is enforced in
  one place and unit-tested independently of the HTTP layer.

## Scalability additions (agent-generated, human-directed)

Added behind env flags so defaults keep the app runnable with no extra infra:

- **Async email** via Celery + Redis worker (`EMAIL_DELIVERY=celery`), inline
  fallback for dev/tests. `app/worker.py`, `app/services/notifications.py`.
- **Rate limiting** on the public endpoint — Redis fixed-window FastAPI
  dependency (`app/core/ratelimit.py`). *(Replaced the agent's first slowapi
  attempt, which broke import — see `AGENT_USAGE.md` example B.)*
- **Idempotency keys** on submit (`app/services/idempotency.py`).
- **S3/MinIO storage** behind the `FileStorage` interface (`app/services/storage.py`,
  `docker-compose.s3.yml`).
- **DB connection pooling** (`app/core/database.py`).

## Correctness / reliability fixes (agent-generated, human-directed)

Found during a self-audit against consistency/availability/reliability:

- **Broker outage no longer breaks submit** — `dispatch_lead_notifications`
  falls back to inline delivery if the Celery enqueue fails.
- **No orphaned resume files** — `create_lead` deletes the stored blob if the
  DB commit fails (added `FileStorage.delete`).
- **Race-free idempotency** — atomic Redis `SET NX` reserve/finalize/release
  replaces the earlier get-then-set (which could let concurrent duplicates both
  create a lead).

## Verification performed

- `pytest` — **15 tests passing** (public submit, validation, auth guards,
  state transitions, resume download, rate-limit parsing, idempotency
  race-safety + fail-open, orphaned-file cleanup).
- Backend + Celery worker modules import cleanly.
- Frontend production build / typecheck run clean.
- Full E2E exercised via Docker Compose (form → queued email in MailHog →
  login → mark reached out).
