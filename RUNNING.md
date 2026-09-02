# Running locally

Two ways to run: **Docker Compose** (recommended, one command) or **manual**
(run each service yourself). Everything runs on your own machine — nothing is
deployed to any server.

---

## Option A — Docker Compose (recommended)

**Prerequisite:** Docker Desktop.

```bash
docker compose up --build
```

This starts four containers:

| Service | URL                       | Purpose                              |
|---------|---------------------------|--------------------------------------|
| web     | http://localhost:3000     | Next.js app                          |
| api     | http://localhost:8000     | FastAPI (`/docs` for Swagger UI)     |
| db      | localhost:5432            | PostgreSQL                           |
| mailhog | http://localhost:8025     | Captures every sent email            |

The API auto-creates tables and seeds an attorney on startup. In compose the
email backend is **SMTP → MailHog**, so submitting a lead produces two messages
you can view at http://localhost:8025.

**Seeded login:** `attorney@example.com` / `changeme123`

To stop: `Ctrl+C`, then `docker compose down` (add `-v` to wipe the DB + uploads).

---

## Option B — Manual (no Docker)

**Prerequisites:** Python 3.12+, Node 18+, and a PostgreSQL instance
(or use SQLite — see note below).

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env        # edit DATABASE_URL if needed
uvicorn app.main:app --reload --port 8000
```

- With no Postgres handy, set in `.env`:
  `DATABASE_URL=sqlite:///./dev.db` and `EMAIL_BACKEND=console`
  (emails print to the API console).
- API runs at http://localhost:8000, Swagger at http://localhost:8000/docs.

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local  # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

App runs at http://localhost:3000.

---

## Running the tests

```bash
cd backend
.\.venv\Scripts\python.exe -m pytest      # Windows
# or: pytest
```

The suite uses a throwaway SQLite DB and a temp upload dir, so no Postgres is
required to run tests.

---

## Email backends

Set `EMAIL_BACKEND` in the environment:

| Value      | Behaviour                                             |
|------------|-------------------------------------------------------|
| `console`  | Prints emails to the API log (default; zero setup).   |
| `smtp`     | Sends via SMTP — MailHog in compose (`localhost:8025`).|
| `sendgrid` | Sends via SendGrid; requires `SENDGRID_API_KEY`.       |

---

## End-to-end walkthrough (for the demo recording)

1. Open http://localhost:3000, fill the form, attach a PDF, submit → success screen.
2. Open http://localhost:8025 (MailHog) → see the prospect + attorney emails.
3. Go to http://localhost:3000/login, sign in as the attorney.
4. On `/leads`, see the new lead as `PENDING`; download its resume.
5. Click **Mark reached out** → state flips to `REACHED_OUT`.
6. Filter by state; log out.
