# Stage 1: build the Vue frontend
FROM node:22-alpine AS frontend
# Short git SHA of the commit being built, baked into the app footer. Computed
# on the host (the build context excludes .git) and passed via --build-arg.
ARG APP_GIT_HASH=unknown
ENV APP_GIT_HASH=$APP_GIT_HASH
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY frontend/ .
RUN npm run build

# Stage 2: Python backend
FROM python:3.12-slim AS builder
WORKDIR /build
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 3: runtime
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    DATA_DIR=/app/data \
    UPLOAD_DIR=/app/uploads \
    PORT=8983 \
    HOST=0.0.0.0
COPY --from=builder /install /usr/local
COPY backend /app
COPY --from=frontend /web/dist /app/frontend_dist
# /app/data and /app/uploads are backed by volumes (see VOLUME below); the
# runtime appuser must own them so it can write the DB and uploads.
RUN useradd -m appuser \
    && mkdir -p /app/data /app/uploads \
    && chown -R appuser:appuser /app/data /app/uploads
USER appuser
EXPOSE 8983
VOLUME ["/app/data", "/app/uploads"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python -c "import os,urllib.request,sys; p=os.environ.get('PORT','8983'); sys.exit(0 if urllib.request.urlopen(f'http://127.0.0.1:{p}/api/health', timeout=4).status==200 else 1)"
CMD ["python", "run.py"]
