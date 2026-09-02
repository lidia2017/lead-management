# Lead Management

A full-stack application for capturing and managing prospect **leads**.

- **Public lead form** — prospects submit first name, last name, email, and a
  resume/CV. No login required.
- **Email notifications** — on submission, both the prospect and an attorney
  are emailed.
- **Internal dashboard** — auth-guarded UI listing every lead with all details.
  Each lead has a **state** (`PENDING` → `REACHED_OUT`) that an attorney can
  advance after reaching out.

## Tech stack

| Layer     | Choice                                              |
|-----------|-----------------------------------------------------|
| Backend   | FastAPI (Python 3.12), SQLModel                     |
| Frontend  | Next.js 14 (App Router, TypeScript)                 |
| Database  | PostgreSQL                                          |
| Files     | Local volume behind a `FileStorage` interface       |
| Email     | Pluggable: console / SMTP (MailHog) / SendGrid      |
| Auth      | JWT bearer tokens, bcrypt-hashed passwords          |

## Repository layout

```
lead-management/
├── SYSTEM_DESIGN.md      # architecture & design rationale
├── RUNNING.md            # how to run locally (Docker + manual)
├── AGENT_USAGE.md        # coding-agent usage writeup + prompt excerpts
├── NOTES.md              # agent-generated vs hand-written attribution
├── docker-compose.yml    # db + mailhog + api + web
├── backend/              # FastAPI app, tests, Dockerfile
└── frontend/             # Next.js app, Dockerfile
```

## Quick start

```bash
docker compose up --build
```

Then open:

- **Public form:** http://localhost:3000
- **Staff login:** http://localhost:3000/login (`attorney@example.com` / `changeme123`)
- **API docs:** http://localhost:8000/docs
- **Sent emails (MailHog):** http://localhost:8025

See **[RUNNING.md](./RUNNING.md)** for the manual (non-Docker) setup and full
details. See **[SYSTEM_DESIGN.md](./SYSTEM_DESIGN.md)** for the design.
