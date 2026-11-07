# BlockCraft Ukraine

Україномовний навігатор по контенту Minecraft: Java Edition. Моди, ресурспаки, шейдери, датапаки, збірки, сервери й скіни — з відкритих джерел (Modrinth, MineSkin, Mojang), підібрані під «Мою гру», з перевіркою сумісності та експортом збірок у `.mrpack`. Шлях гравця: знайти → взяти → поділитися.

- Бекенд: Django 5.2 + DRF, Celery, PostgreSQL 17, Redis 7, Meilisearch (`backend/`).
- Фронтенд: Next.js 16 + React 19 + TypeScript, Tailwind CSS 4 (`frontend/`).
- Інфраструктура: Docker Compose, Nginx (один origin для фронтенду й API).

Продукт — [`docs/product.md`](docs/product.md), специфікація й етапи ребілду R0–R9 — [`docs/tech.md`](docs/tech.md), прогрес — [`docs/PROGRESS.md`](docs/PROGRESS.md), аудит v1 — [`docs/rebuild/audit.md`](docs/rebuild/audit.md). Перша версія — [`docs/archive/v1/`](docs/archive/v1/).

## Що потрібно встановити

| Інструмент | Навіщо | Windows |
| --- | --- | --- |
| Docker Desktop | Увесь стек розробки | [docker.com](https://www.docker.com/products/docker-desktop/) |
| Git | Код | `winget install Git.Git` |
| GNU Make | Команди `make …` | `winget install ezwinports.make` |
| Node.js 24 LTS + pnpm | Необов'язково: фронтенд на хості (`make up-local`) | `winget install OpenJS.NodeJS.LTS`, потім `corepack enable` |
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

Міграції застосовуються автоматично під час старту бекенду. Каталог модів наповнює `make sync-mods` (≈ 500 проєктів з Modrinth, кілька хвилин; далі — щоночі через Celery beat). Зупинити — `make down`.

### Windows: фронтенд на хості

На Windows-дисках зміни файлів не доходять до контейнера, тому hot reload фронтенду в Docker не працює (бекенд перезавантажується сам — Django опитує свої файли). Для роботи над фронтендом запускай його локально, решту — в Docker:

```bash
make up-local          # усе, крім frontend; Nginx проксіює на host.docker.internal:3000
cd frontend
pnpm install
pnpm dev               # сайт однаково відкривається на http://localhost:8080
```

Команди фронтенду тоді запускай з `FRONTEND_LOCAL=1`, наприклад `make lint FRONTEND_LOCAL=1`.

### Пошта й вхід через Discord / Google

- У dev листи (підтвердження пошти, скидання пароля) не надсилаються, а друкуються в лог бекенду: `make logs` → посилання `http://localhost:8080/verify-email/…`.
- Кнопки Discord і Google з'являються, щойно в `.env` заповнені `DISCORD_CLIENT_ID` / `DISCORD_CLIENT_SECRET` або `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` (після зміни — `make down && make up`). Redirect URI в налаштуваннях застосунку провайдера:
  - Discord: `http://localhost:8080/accounts/discord/login/callback/`
  - Google: `http://localhost:8080/accounts/google/login/callback/`

## Команди

| Команда | Що робить |
| --- | --- |
| `make up` / `make down` / `make logs` / `make ps` | Підняти / зупинити / логи / список контейнерів |
| `make sh-back` / `make sh-front` | Shell у контейнері бекенду / фронтенду |
| `make migrate` / `make makemigrations` / `make createsuperuser` | Django management |
| `make test` / `make test-back` / `make test-front` | pytest (з покриттям) і Vitest |
| `make lint` / `make fmt` / `make typecheck` | ruff, ESLint, Prettier, `tsc --noEmit` |
| `make api-types` | Експорт схем API (`frontend/openapi.yaml`, `frontend/allauth-openapi.json`) і генерація типів `schema.d.ts` / `allauth.d.ts` у `frontend/src/lib/api/` |
| `make reset-db` | Видалити й створити БД заново (міграції — під час старту бекенду) |
| `make sync-mods` | Синхронізація модів, ресурспаків і шейдерів з Modrinth |
| `make seed` | Демо-гравці поверх синхронізованих даних (спершу `make sync-mods`): 20 гравців (пароль `Creeper-Aww-Man-2026`), обране, колекції, відгуки, збірки; `--reset` — створити заново |
| `make reindex` | Перебудувати пошуковий індекс Meilisearch |
| `make er-diagram` | ER-діаграма моделей у Mermaid (v1: `docs/archive/v1/coursework/er.md`) |

e2e (Playwright): `ACCOUNT_EMAIL_VERIFICATION=none docker compose up -d`, `sync_mods --limit 20`, `make seed`, далі тести з `e2e/` — див. джоб `e2e` у `.github/workflows/ci.yml`. Продакшн і деплой — [docs/deploy.md](docs/deploy.md).

Один тест бекенду: `docker compose exec backend uv run pytest apps/core/tests/test_health.py -k redis`.

## Pre-commit

```bash
uv tool install pre-commit
pre-commit install
```

Хуки: ruff, Prettier, ESLint, gitleaks (секрети), великі файли, закінчення рядків LF. Хуки фронтенду виконуються в контейнері `frontend`, тому перед комітом змін у `frontend/` стек має бути запущений (`make up`); Node.js на хості не потрібен.

## Структура

```
backend/     Django: config/ (налаштування base/dev/test/prod, Celery), apps/<name>/
frontend/    Next.js: src/app (маршрути), src/features, src/components, src/lib/api
infra/       Nginx (dev, prod, заголовки безпеки), скрипти TLS і резервних копій
e2e/         Playwright: ключові сценарії
docs/        Продукт, специфікація, прогрес, деплой, аудит ребілду; v1 — docs/archive/v1
```

Не є офіційним продуктом Minecraft. Не пов'язано з Mojang або Microsoft.
