# Recurring Payments App

Single-service recurring USD→GHS billing app for Railway (FastAPI + embedded scheduler in one service) with a managed PostgreSQL database.

The embedded scheduler now includes a process-level lock to prevent overlapping invoice runs inside the same service instance.

## Quick start (local)

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Open:
- `http://localhost:8000/`
- `http://localhost:8000/docs`
- `http://localhost:8000/health`

## Required environment variables

- `DATABASE_URL` (Railway PostgreSQL connection string, e.g. `postgresql+psycopg://USER:PASSWORD@HOST:PORT/railway`)
- `JWT_SECRET`
- `CORS_ORIGINS` (must be explicit, e.g. `https://billing.yourdomain.com`)
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `FROM_EMAIL`
- `ENABLE_SCHEDULER` (`true`/`false`)
- `SCHEDULER_INTERVAL_MINUTES` (e.g. `1440`)
- `JSON_LOGS` (`true` recommended in Railway)
- `ENABLE_ALERT_EMAILS` (`true`/`false`, optional)
- `ALERT_EMAIL` (required when `ENABLE_ALERT_EMAILS=true`)

## Main endpoints

- `GET /`
- `GET /health`
- `POST /auth/login` (JWT auth)
- `POST /users`, `GET /users`, `PATCH /users/{user_id}` (superadmin only)
- `POST /clients`, `GET /clients`, `DELETE /clients/{client_id}`
- `POST /projects`, `GET /projects`, `DELETE /projects/{project_id}`
- `POST /rates`, `GET /rates`
- `POST /rates/parse-pdf`, `POST /rates/ingest-pdf`
- `POST /projects/{project_id}/invoice?invoice_date=YYYY-MM-DD`
- `GET /invoices`
- `GET /jobs`
- `POST /run-jobs-now`

Protected endpoints now require `Authorization: Bearer <token>` from `/auth/login`.
Default seeded superadmin credentials:
- username: `superadmin`
- password: `Nankani1`

PDF rate parsing uses table extraction first, then plain-text fallback, then OCR fallback for scanned/image-only PDFs (requires `tesseract` binary in runtime).

Scheduler execution uses a database-backed distributed lock (`scheduler_locks`) to reduce duplicate runs across multiple instances.

See `infra/railway/README.md` for deployment.

## Tests

- Unit tests: `apps/api/tests/test_config.py`, `test_pdf_rates.py`, `test_services.py`
- Basic API integration tests: `apps/api/tests/test_api_integration.py`

CI is included at `.github/workflows/ci.yml` and runs API tests plus a web build on push/PR.
