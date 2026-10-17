# BlockCraft Ukraine

Україномовна платформа спільноти Minecraft: моди, зборки, скіни й сервери — знайти, зберегти, поділитися своїм.

- Бекенд: Django 5.2 + DRF, Celery, PostgreSQL 17, Redis 7, Meilisearch (`backend/`).
- Фронтенд: Next.js 16 + React 19 + TypeScript, Tailwind CSS 4 (`frontend/`).
- Інфраструктура: Docker Compose, Nginx (один origin для фронтенду й API).

Специфікація й етапи — [`docs/tech.md`](docs/tech.md), прогрес — [`docs/PROGRESS.md`](docs/PROGRESS.md).

## Що потрібно встановити

| Інструмент | Навіщо | Windows |
| --- | --- | --- |
| Docker Desktop | Увесь стек розробки | [docker.com](https://www.docker.com/products/docker-desktop/) |
| Git | Код | `winget install Git.Git` |
| GNU Make | Команди `make …` | `winget install ezwinports.make` |
| Node.js 24 LTS + pnpm | Фронтенд на хості, pre-commit | `winget install OpenJS.NodeJS.LTS`, потім `corepack enable` |
| uv | Python-залежності на хості (IDE, pre-commit) | `winget install astral-sh.uv` |

## Запуск з нуля

```bash
git clone https://github.com/kazzutora/web-platform-BlockCraft-Ukraine.git
cd web-platform-BlockCraft-Ukraine
make up
```

`make up` створює `.env` з `.env.example` (якщо його ще немає), збирає образи й піднімає `db`, `redis`, `meili`, `backend`, `worker`, `beat`, `frontend`, `nginx`. Перший запуск триває кілька хвилин.

- http://localhost:8080 — сайт (стартова сторінка показує статус API: `ok`)
- http://localhost:8080/api/docs/ — Swagger UI, схема — `/api/schema/`
- http://localhost:8080/api/v1/health — перевірка БД і Redis
- http://localhost:8080/admin/ — адмінка (`make createsuperuser`)

Міграції застосовуються автоматично під час старту бекенду. Зупинити — `make down`.

### Windows: фронтенд на хості

У Docker на Windows зміни файлів доходять до контейнера лише через опитування (раз на секунду), тому hot reload фронтенду повільніший. Швидший варіант — фронтенд локально, решта в Docker:

```bash
make up-local          # усе, крім frontend; Nginx проксіює на host.docker.internal:3000
cd frontend
pnpm install
pnpm dev               # сайт однаково відкривається на http://localhost:8080
```

Команди фронтенду тоді запускай з `FRONTEND_LOCAL=1`, наприклад `make lint FRONTEND_LOCAL=1`.

## Команди

| Команда | Що робить |
| --- | --- |
| `make up` / `make down` / `make logs` / `make ps` | Підняти / зупинити / логи / список контейнерів |
| `make sh-back` / `make sh-front` | Shell у контейнері бекенду / фронтенду |
| `make migrate` / `make makemigrations` / `make createsuperuser` | Django management |
| `make test` / `make test-back` / `make test-front` | pytest (з покриттям) і Vitest |
| `make lint` / `make fmt` / `make typecheck` | ruff, ESLint, Prettier, `tsc --noEmit` |
| `make api-types` | Експорт OpenAPI-схеми в `frontend/openapi.yaml` і генерація `frontend/src/lib/api/schema.d.ts` |
| `make reset-db` | Видалити й створити БД заново (міграції — під час старту бекенду) |
| `make seed`, `make sync-mods` | Демо-дані (етап 9) і синхронізація з Modrinth (етап 3) |

Один тест бекенду: `docker compose exec backend uv run pytest apps/core/tests/test_health.py -k redis`.

## Pre-commit

```bash
uv tool install pre-commit
pre-commit install
```

Хуки: ruff, Prettier, ESLint, gitleaks (секрети), великі файли, закінчення рядків LF. Хуки фронтенду викликають `pnpm` на хості, тому потрібні Node.js і `pnpm install` у `frontend/`.

## Структура

```
backend/     Django: config/ (налаштування base/dev/test/prod, Celery), apps/<name>/
frontend/    Next.js: src/app (маршрути), src/features, src/components, src/lib/api
infra/       Nginx-конфіги, скрипти
docs/        Специфікація, прогрес, матеріали курсової
```

Не є офіційним продуктом Minecraft. Не пов'язано з Mojang або Microsoft.
