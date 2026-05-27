# Railway deployment guide (ONE app service + PostgreSQL)

This setup uses **one Railway service** for the app (API + scheduler in one process) and a **Railway PostgreSQL plugin** for durable production data.

## 1) Create project from GitHub
- Railway → New Project → Deploy from GitHub Repo.
- Select this repo.

## 2) Add PostgreSQL plugin
- In the same Railway project, click **New** → **Database** → **Add PostgreSQL**.
- Copy the generated Postgres connection string for `DATABASE_URL`.

## 3) Configure only ONE app service
- Service root directory: `apps/api`
- Build command: `pip install -r requirements.txt`
- Start command: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`

## 4) Environment variables
Required:
- `DATABASE_URL` (use Railway Postgres URL, e.g. `postgresql+psycopg://USER:PASSWORD@HOST:PORT/railway`)
- `JWT_SECRET`
- `CORS_ORIGINS` (example: `https://your-app.up.railway.app`)
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `FROM_EMAIL`
- `ENABLE_SCHEDULER=true`
- `SCHEDULER_INTERVAL_MINUTES=1440`
- `JSON_LOGS=true`
- `ENABLE_ALERT_EMAILS=false` (set true to email operational failures)
- `ALERT_EMAIL` (required if alerts are enabled)

## 5) Public URL
- In service Settings → Networking, generate a public domain.
- Open in browser:
  - `/` for landing page
  - `/docs` for API docs
  - `/health` for status

## 6) Custom domain
- Add custom domain directly to this same app service (e.g., `billing.yourdomain.com`).
- Add DNS record Railway gives you.
- Wait for SSL to provision.

## 7) Notes
- This is still a low-complexity deployment (one app service + managed DB).
- For better reliability/scaling later, you can split background worker into a second app service.
