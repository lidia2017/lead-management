# Lead Management — System Design

## 1. Problem statement

Build an application that supports **creating, getting, and updating leads**.

- A **lead** is a form that is **publicly** available for prospects to fill in.
  Required fields: `first name`, `last name`, `email`, `resume / CV`.
- On submission the system sends emails to **both** the prospect and an
  **attorney** inside the company.
- An **internal UI** (guarded by auth) renders the list of leads with all the
  data the prospect filled in.
- Each lead has a **state**: it starts at `PENDING` and transitions to
  `REACHED_OUT` when an attorney manually marks it after reaching out.

## 2. High-level architecture

Each component is its own box/service. The **request path** (solid, top→down)
stays fast; the slow email work is handed to Redis and processed on a separate
**async path** (the worker) so a submission never waits on mail delivery.

```
                          Public internet
                                │
             ┌──────────────────┴───────────────────┐
             │                                       │
      Prospect (public)                     Attorney (authenticated)
             │                                       │
             └──────────────────┬────────────────────┘
                                ▼
                     ┌──────────────────────┐
                     │     Next.js web app   │  public form · login · dashboard
                     └───────────┬──────────┘
                                 │  HTTPS  (JSON + multipart)
                                 ▼
                     ┌──────────────────────┐
                     │     Load balancer     │  TLS · WAF · CDN for static assets
                     └───────────┬──────────┘
                                 ▼
             ┌───────────────────────────────────────────┐
             │        FastAPI  (stateless · scale to N)    │
             │  JWT auth · state machine · validation ·    │
             │  rate limiting · idempotency                │
             └──┬───────────────┬───────────────┬──────┬──┘
     write/read │        store  │      use      │      │  enqueue email job
     lead+user  │        resume │      Redis    │      │  (returns 201 now)
                ▼               ▼               ▼      ▼
        ┌──────────────┐ ┌────────────┐ ┌───────────────────────┐
        │  PostgreSQL   │ │ File store │ │        Redis           │
        │  leads, users │ │ local vol  │ │  • Celery broker       │
        │  pool +       │ │ or S3/MinIO│ │  • rate-limit counters │
        │  read replicas│ │            │ │  • idempotency keys    │
        └──────────────┘ └────────────┘ └───────────┬───────────┘
                                                     │  worker consumes jobs
                                                     ▼
                                          ┌────────────────────┐
                                          │  Celery worker pool │  retries +
                                          │  (scale to M)       │  backoff
                                          └──────────┬─────────┘
                                                     ▼
                                          ┌────────────────────┐
                                          │  Email service      │  console /
                                          │  (pluggable)        │  SMTP(MailHog)
                                          └──────────┬─────────┘  / SendGrid
                                                     ▼
                                     emails to prospect + attorney
```

Boxes actually implemented in this repo: Next.js, FastAPI (with JWT, the state
machine, rate limiting, idempotency), PostgreSQL, the local/S3 file store,
Redis, the Celery worker, and the pluggable email service. The **load balancer**
and multiple **API replicas / read replicas** are the deployment-time scale-out
seam — the app is stateless and storage/email sit behind interfaces, so adding
them requires no code change (see §7).

## 3. Data model

### `leads`
| column            | type        | notes                                   |
|-------------------|-------------|-----------------------------------------|
| id                | UUID (PK)   |                                         |
| first_name        | text        | required                                |
| last_name         | text        | required                                |
| email             | text        | required, validated                     |
| resume_filename   | text        | original filename                       |
| resume_path       | text        | path on the file volume                 |
| resume_content_type | text      | mime type                               |
| state             | enum        | `PENDING` \| `REACHED_OUT`, default PENDING |
| created_at        | timestamptz |                                         |
| updated_at        | timestamptz |                                         |

### `users` (attorneys / internal staff)
| column          | type        | notes                        |
|-----------------|-------------|------------------------------|
| id              | UUID (PK)   |                              |
| email           | text unique | login identifier             |
| hashed_password | text        | bcrypt                       |
| full_name       | text        |                              |
| role            | text        | `attorney` (default)         |
| created_at      | timestamptz |                              |

### State machine
```
PENDING ──(attorney marks reached out)──▶ REACHED_OUT
```
Only `PENDING → REACHED_OUT` is allowed. Any other transition is rejected with
`409 Conflict`. The transition is manual and requires authentication.

## 4. API surface

| Method | Path                      | Auth | Purpose                              |
|--------|---------------------------|------|--------------------------------------|
| POST   | `/api/leads`              | ❌   | Public form submit (multipart)       |
| GET    | `/api/leads`              | ✅   | List leads (filter by state, paged)  |
| GET    | `/api/leads/{id}`         | ✅   | Lead detail                          |
| PATCH  | `/api/leads/{id}`         | ✅   | Update state (PENDING→REACHED_OUT)   |
| GET    | `/api/leads/{id}/resume`  | ✅   | Download the resume                  |
| POST   | `/api/auth/login`         | ❌   | Exchange email/password for a JWT    |
| GET    | `/api/auth/me`            | ✅   | Current user                         |
| GET    | `/api/health`             | ❌   | Liveness probe                       |

## 5. Key flows

### Lead submission (public)
1. Prospect submits the form (multipart: fields + resume file).
2. API validates fields + file (type/size), persists the file to the volume,
   inserts a `PENDING` lead row.
3. API schedules two emails via a **BackgroundTask** so the HTTP response is
   fast: a confirmation to the prospect and a notification to the attorney.
4. Returns the created lead (201).

### Attorney workflow (internal)
1. Attorney logs in → receives a JWT (stored client-side).
2. `/leads` fetches the list with the bearer token; can filter by state.
3. Attorney reviews a lead, downloads the resume, and marks it `REACHED_OUT`.

## 6. Design decisions & trade-offs

- **Pluggable email service** — an `EmailService` interface with `console`
  (dev), `smtp` (MailHog / any SMTP), and a `sendgrid`/`ses` adapter selectable
  via `EMAIL_BACKEND`. Keeps the app runnable with zero external accounts while
  proving the integration seam. Emails are sent in a background task so a slow
  provider never blocks form submission.
- **Local file storage behind a `FileStorage` interface** — resumes live on a
  mounted volume in dev; the interface makes swapping in S3/GCS a one-class
  change. DB stores only metadata + path, never the blob.
- **Postgres + SQLModel** — typed models shared between ORM and validation.
  Migrations via `SQLModel.metadata.create_all` for the take-home; a
  production repo would use Alembic (noted, stubbed).
- **JWT auth** — stateless bearer tokens, bcrypt-hashed passwords, a seeded
  attorney. Simple to reason about and to guard the internal routes with a
  FastAPI dependency.
- **State transitions validated server-side** — the client cannot force an
  illegal transition; the rule lives in the service layer.

## 7. Scaling for load

The app is built so scaling is a matter of **configuration and topology**, not
rewrites. The public submit path (spiky, bot-prone) and the internal dashboard
(low traffic) scale independently.

### Implemented in this repo (toggle via env; on by default in Docker)

- **Async email via a queue** (`EMAIL_DELIVERY=celery`). The API enqueues a job
  to **Redis** and returns `201` immediately; a separate **Celery worker** pool
  sends the mail with automatic retries + exponential backoff. A slow/down mail
  provider can no longer block or lose a submission, and the workers scale on
  their own (`docker compose up --scale worker=3`). Falls back to an in-process
  `BackgroundTask` when set to `inline` (dev/tests).
- **Rate limiting** on the public endpoint (`RATE_LIMIT_ENABLED=true`), a per-IP
  fixed window backed by Redis so the limit is shared across all API replicas.
  Sheds bot/spam load before it hits the DB or mail pipeline. Fail-open.
- **Idempotency** on the public endpoint (`IDEMPOTENCY_ENABLED=true`) via an
  `Idempotency-Key` header stored in Redis — double-clicks / client retries
  return the original lead instead of creating duplicates.
- **Object storage** for resumes (`STORAGE_BACKEND=s3`) behind the existing
  `FileStorage` interface, so many stateless API replicas share one durable
  store instead of local disk. Demonstrated with MinIO (`docker-compose.s3.yml`).
- **DB connection pooling** tuned per replica (`DB_POOL_SIZE`, `DB_MAX_OVERFLOW`).

### Topology it enables

Same components as §2, scaled out: the API fans out behind a load balancer, the
data stores each scale on their own axis, and the async email path runs on an
independently-scaled worker pool.

```
                 Prospect / Attorney browsers
                             │
                             ▼
                 ┌────────────────────────┐
                 │    CDN  +  Next.js web   │   static assets cached at edge
                 └────────────┬───────────┘
                              ▼
                 ┌────────────────────────┐
                 │    Edge / WAF            │   TLS · rate limit · CAPTCHA
                 └────────────┬───────────┘
                              ▼
                 ┌────────────────────────┐
                 │      Load balancer       │
                 └────────────┬───────────┘
                              ▼
       ┌────────────────────────────────────────────┐
       │   Stateless FastAPI replicas (autoscaled)     │
       │        api-1    api-2    ...    api-N          │
       └──┬───────────────┬────────────────┬──────────┘
   pooled │         use   │        enqueue  │   put/get resume
    conns │        Redis  │        email    │   (presigned URL)
          ▼               ▼                 ▼
   ┌────────────┐   ┌───────────────┐   ┌──────────────┐
   │ PgBouncer   │   │    Redis       │   │  S3 / MinIO   │
   │     │       │   │  broker +      │   │  object store │
   │     ▼       │   │  rate-limit +  │   └──────────────┘
   │ PostgreSQL  │   │  idempotency   │
   │ primary     │   └───────┬───────┘
   │   │ replicate│           │  workers consume
   │   ▼         │           ▼
   │ read        │   ┌────────────────────┐
   │ replicas    │   │ Celery worker pool   │  retries + backoff
   └────────────┘   │ (autoscaled)         │  + dead-letter queue
                    └──────────┬─────────┘
                               ▼
                    ┌────────────────────┐
                    │  Email provider      │  SES / SendGrid
                    └────────────────────┘
```

Because auth is stateless (JWT), storage and email sit behind interfaces, and
business rules live in the service layer, each box above is swappable/scalable
without touching application logic. Reads (dashboard) hit Postgres **read
replicas** while writes go to the **primary**; the public write path and the
async email path each scale independently of the low-traffic dashboard.

### Next steps if traffic grew further

- Postgres **read replicas** for the dashboard's read-heavy queries; keyset
  pagination instead of `OFFSET`.
- **Presigned S3 URLs** so resume bytes never transit the API.
- Dead-letter queue + alerting on worker failures; CAPTCHA at the edge.

## 8. Production hardening (out of scope, noted)

- Alembic migrations, connection pooling tuning.
- Object storage (S3) + presigned upload/download URLs + virus scanning of
  resumes.
- Rate limiting / CAPTCHA on the public endpoint to stop spam.
- Refresh tokens + short-lived access tokens, RBAC, audit log of state changes.
- Idempotency keys on submit; retryable email delivery via a queue (SQS/Celery).
- Observability: structured logs, metrics, tracing, error tracking.
- CI/CD, infra-as-code, secrets manager instead of `.env`.
```