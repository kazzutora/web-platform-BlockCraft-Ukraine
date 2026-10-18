# Two targets: `dev` (dev dependencies, code bind-mounted by docker-compose.yml)
# and `prod` (no dev dependencies, code baked in, Gunicorn with Uvicorn workers).
FROM python:3.13-slim AS base

COPY --from=ghcr.io/astral-sh/uv:0.12.10 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app


FROM base AS dev

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

COPY . .

EXPOSE 8000

CMD ["uv", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]


FROM base AS prod

ENV ENV=prod \
    UV_NO_SYNC=1

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

COPY . .

# Static files are collected into the image; Nginx gets them through a shared volume
RUN SECRET_KEY=collectstatic-only COLLECTSTATIC_BUILD=1 DATABASE_URL=sqlite:///tmp/build.db \
    REDIS_URL=redis://localhost:6379/0 \
    python manage.py collectstatic --noinput

# Volumes copy the ownership of these directories when they are created
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /app/media /app/staticfiles-shared \
    && chown -R app /app/media /app/staticfiles-shared
USER app

EXPOSE 8000

# Two workers per CPU is plenty for a small VPS; ASGI for the real-time features later
CMD ["gunicorn", "config.asgi:application", "-k", "uvicorn_worker.UvicornWorker", \
     "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60", "--access-logfile", "-"]
