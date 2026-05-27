# Stage 1: Build Next.js frontend
FROM node:20-slim AS web-builder
WORKDIR /web
COPY apps/web/package*.json ./
RUN npm install
COPY apps/web/ ./
# Empty = same origin, so the frontend calls the API on the same domain
ENV NEXT_PUBLIC_API_BASE_URL=""
RUN npm run build

# Stage 2: Python API + embedded frontend
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY apps/api/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY apps/api/ ./
# Embed the Next.js static export so FastAPI can serve it
COPY --from=web-builder /web/out ./web_out
EXPOSE 8000
CMD export PYTHONPATH=/app && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
