# BlockCraft Ukraine — технічна специфікація

Це головне джерело правди для розробки. Продуктовий опис (суть, сценарії, дизайн) — у документі «BlockCraft Ukraine — аналіз проєкту»; тут — як це будувати.

**Як читати:** розділи 1–9 — довідник (архітектура, стек, структура, моделі, API, фронтенд, задачі у фоні). Розділ 10 — етапи розробки з задачами й критеріями готовності. Під час роботи над етапом читай розділ цього етапу й лише ті довідкові розділи, на які він посилається.

**Якщо реалізація відходить від цього документа** — це нормально, але рішення записується в `docs/PROGRESS.md` → «Журнал рішень», а цей файл оновлюється в тому ж коміті.

---

## 1. Продукт коротко

Україномовна платформа спільноти Minecraft: знайти (моди, зборки, скіни, сервери, світи) → зберегти (обране, колекції, сетап) → поділитися своїм (скіни, моменти, зборки, сервери). Не форум і не маркетплейс. Дизайн — спокійний редакційний мінімалізм із блоковими акцентами; 3D лише для скінів.

**MVP для курсової (етапи 0–9):** акаунти + онбординг, моди (Modrinth), скіни, сервери, обране й колекції, оцінки/відгуки/коментарі, пошук, головна, модерація, деплой.

**Після MVP (етапи 10–18):** зборки й `.mrpack`, моменти з відео, світи, челенджі, сетап і стрічка, рівні й real-time сповіщення, історія й відстеження оновлень, кабінет власника сервера, англійська мова.

**Команда:** 1 розробник + Claude Code. Звідси принципи: мінімум сервісів, нудні перевірені технології, все запускається однією командою, кожен етап закінчується робочою версією.

---

## 2. Архітектура

```
Браузер ──HTTPS──> Nginx ──/            ──> Next.js (SSR + клієнт)
                         ├─/api/        ──> Django + DRF (Gunicorn/Uvicorn)
                         ├─/_allauth/   ──> Django (allauth headless)
                         ├─/admin/      ──> Django admin
                         └─/media/      ──> файли (dev: том; prod: S3-сумісне)

Next.js (сервер) ──http://backend:8000──> Django   (SSR-запити з пересиланням cookie)

Django ──> PostgreSQL · Redis (кеш, сесії, брокер) · Meilisearch (пошук)
Celery worker + beat ──> Modrinth API · Mojang API · Minecraft-сервери (Server List Ping)
```

Ключові рішення:

- **Один домен, один origin.** Nginx віддає фронтенд і бекенд з одного домену → авторизація на сесійних cookie + CSRF, без CORS і без JWT у браузері.
- **Django — лише API + адмінка.** Жодних Django-шаблонів для користувача.
- **SSR для каталогів і сторінок об'єктів** (SEO, швидкий перший екран); мутації (зберегти, оцінити) — з клієнта через TanStack Query з оптимістичним оновленням.
- **Усе повільне — у Celery:** синхронізація з Modrinth, пінг серверів, обробка зображень, перерахунок рейтингів, індексація пошуку.
- **Типи API генеруються** з OpenAPI-схеми (drf-spectacular → openapi-typescript), руками DTO на фронтенді не пишемо.

---

## 3. Стек і версії

Версії фіксуються в lock-файлах на етапі 0; нижче — мінімальні цільові.

### Бекенд
| Пакет | Версія | Навіщо |
| --- | --- | --- |
| Python | 3.13 | Мова |
| uv | актуальна | Менеджер залежностей і venv |
| Django | 5.2 LTS | Фреймворк (LTS до квітня 2028; на 6.x переходимо лише якщо всі залежності сумісні) |
| djangorestframework | 3.16+ | REST API |
| django-filter | актуальна | Фільтри каталогів |
| drf-spectacular | актуальна | OpenAPI-схема, Swagger UI |
| django-allauth[socialaccount] | 65+ | Реєстрація, вхід, Discord/Google, headless-режим |
| psycopg[binary] | 3.x | Драйвер PostgreSQL |
| django-redis | актуальна | Кеш і сесії в Redis |
| celery | 5.5+ | Фонові задачі (розклад — через `CELERY_BEAT_SCHEDULE` у налаштуваннях) |
| httpx | актуальна | HTTP-клієнт для Modrinth/Mojang |
| pydantic | 2.x | Схеми відповідей зовнішніх API |
| mcstatus | актуальна | Пінг Minecraft-серверів |
| Pillow | актуальна | Перевірка скінів, прев'ю, банери |
| meilisearch (python) | актуальна | Клієнт пошуку |
| django-storages[s3] | актуальна | S3-сумісне сховище в prod (етап 11) |
| gunicorn + uvicorn | актуальна | Prod-сервер (ASGI для Channels на етапі 15) |
| channels + channels-redis | актуальна | WebSocket (етап 15) |

Розробка: `ruff` (лінтер + форматер), `pytest`, `pytest-django`, `pytest-cov`, `factory-boy`, `respx` (мок httpx), `freezegun`, `django-debug-toolbar` (лише dev), `mypy` + `django-stubs` (поступово, не блокує CI до етапу 9).

### Фронтенд
| Пакет | Версія | Навіщо |
| --- | --- | --- |
| Node.js | 24 LTS | Рантайм |
| pnpm | актуальна | Менеджер пакетів |
| Next.js | 16.x (App Router) | Фреймворк, SSR |
| React | 19 | UI |
| TypeScript | 5.x, `strict: true` | Типи |
| Tailwind CSS | 4.x | Стилі через токени |
| @tanstack/react-query | 5.x | Запити, кеш, оптимістичні оновлення |
| openapi-typescript + openapi-fetch | актуальна | Типізований клієнт API з OpenAPI-схеми |
| react-hook-form + zod | актуальна | Форми й валідація |
| next-themes | актуальна | Світла/темна тема |
| motion | актуальна | Анімації (колишній Framer Motion) |
| skinview3d | актуальна | 3D-перегляд скінів |
| pixelarticons (або власні SVG) | актуальна | Піксельні іконки |

Розробка: ESLint, Prettier, Vitest + Testing Library, Playwright (e2e з етапу 9).

### Інфраструктура
PostgreSQL 17, Redis 7, Meilisearch 1.x, Nginx, Docker + Docker Compose, GitHub Actions, VPS користувача (mvps.net).

**Сховище файлів:** до етапу 11 — локальна файлова система (Docker-том `media`, роздає Nginx). На етапі 11 — S3-сумісне сховище (Cloudflare R2 або аналог) через django-storages; перемикання лише налаштуваннями `STORAGES`.

---

## 4. Структура репозиторію

```
blockcraft/
├── CLAUDE.md                  # правила для Claude Code
├── Makefile                   # усі команди розробки
├── docker-compose.yml         # dev
├── docker-compose.prod.yml    # prod (етап 9)
├── .env.example               # усі змінні з коментарями
├── .pre-commit-config.yaml
├── .github/workflows/ci.yml
├── docs/
│   ├── tech.md                # цей файл
│   ├── PROGRESS.md            # трекер етапів і журнал рішень
│   └── coursework/            # діаграми й матеріали для пояснювальної записки
├── .claude/                   # skills, agents, rules, settings для Claude Code
├── infra/
│   ├── nginx/dev.conf
│   ├── nginx/prod.conf
│   └── scripts/               # backup.sh, entrypoint-и
├── backend/
│   ├── pyproject.toml, uv.lock, Dockerfile, manage.py
│   ├── config/
│   │   ├── settings/{base,dev,test,prod}.py
│   │   ├── urls.py, api_urls.py, asgi.py, wsgi.py, celery.py
│   └── apps/
│       ├── core/              # kinds-реєстр, міксини, пагінація, обробник помилок, health
│       ├── accounts/          # User, GameProfile, UserSettings, Follow, Badge
│       ├── library/           # Favorite, Collection, CollectionItem, ViewHistory, Download
│       ├── social/            # Like, Review, ReviewVote, Comment
│       ├── mods/              # Project, ProjectVersion, Category, Modrinth-клієнт
│       ├── skins/             # Skin, Mojang-клієнт
│       ├── servers/           # Server, ServerSnapshot, пінг
│       ├── search/            # Meilisearch-індекси
│       ├── moderation/        # Report, Sanction, фільтр лексики
│       ├── notifications/     # Notification
│       ├── packs/             # етап 10
│       ├── moments/           # етап 11
│       ├── worlds/            # етап 12
│       └── community/         # Challenge — етап 13
└── frontend/
    ├── package.json, pnpm-lock.yaml, next.config.ts, Dockerfile
    ├── public/illustrations/  # воксельні ілюстрації розділів
    ├── src/
    │   ├── app/               # маршрути App Router (див. розділ 7)
    │   ├── components/ui/     # примітиви дизайн-системи
    │   ├── components/layout/ # Header, Footer, MobileTabBar, шаблони сторінок
    │   ├── features/<name>/   # компоненти й хуки конкретних розділів (mods, skins, …)
    │   ├── lib/api/           # schema.d.ts (генерується), client.ts, server-client.ts
    │   ├── lib/               # утиліти, query-keys, formatters
    │   └── styles/            # globals.css, tokens.css
    └── e2e/                   # Playwright
```

### Структура Django-застосунку
```
apps/<name>/
├── models.py        # лише поля, Meta, прості властивості
├── services.py      # зміни стану: create_*, update_*, бізнес-логіка, транзакції
├── selectors.py     # читання: складні queryset-и для API
├── serializers.py
├── views.py         # ViewSet-и/APIView — тонкі, викликають services/selectors
├── urls.py
├── filters.py       # django-filter
├── permissions.py
├── tasks.py         # Celery
├── clients.py       # зовнішні API (за потреби)
├── admin.py
└── tests/           # test_models.py, test_services.py, test_api.py, factories.py
```

---

## 5. Модель даних

### 5.1 Спільні абстракції (`apps/core`)

**Kinds-реєстр.** Кожен тип контенту, який можна зберегти, оцінити, прокоментувати чи поскаржитися, має рядковий `kind`:

| kind | Модель | URL-ідентифікатор | Оцінка |
| --- | --- | --- | --- |
| `mod` | mods.Project (type=mod/resourcepack/shader) | slug | Review 1–5 |
| `skin` | skins.Skin | id | Like |
| `server` | servers.Server | slug | Review 1–5 |
| `collection` | library.Collection | id | Like |
| `pack` | packs.Pack (етап 10) | slug | Review 1–5 |
| `moment` | moments.Moment (етап 11) | id | Like |
| `world` | worlds.World (етап 12) | slug | Review 1–5 |

`apps/core/kinds.py` містить реєстр `kind → модель`, функцію `resolve(kind, id_or_slug)` і перелік дозволених дій для кожного kind. Узагальнені зв'язки зберігаються через `content_type` + `object_id` (GenericForeignKey) з індексом `(content_type, object_id)`.

**Абстрактні міксини:**
- `TimeStamped`: `created_at`, `updated_at`.
- `Authored`: `author` FK → User.
- `Publishable`: `status` (draft / pending / published / rejected / hidden), `rejection_reason`, `published_at`. Менеджер `.published()`.
- `Engagement` (денормалізовані лічильники): `likes_count`, `favorites_count`, `comments_count`, `downloads_count`, `views_count`, `rating_avg`, `rating_count`, `score` (байєсівське середнє), `trend_score`.

### 5.2 Таблиці MVP

**accounts**
- `User` (AbstractUser, вхід за email): `email` (unique), `nickname` (unique, 3–24, `[a-zA-Z0-9_]`), `avatar`, `bio` (≤ 160), `mc_nickname` (nullable), `role` (user / trusted / moderator / admin), `xp`, `level`, `is_private`, `published_count`.
- `GameProfile` (1:1): `game_version` (напр. "1.21.4"), `loader` (fabric / forge / neoforge / quilt / vanilla), `edition` (java / bedrock), `interests` (ArrayField: survival, building, tech, pvp, rp, …), `onboarding_done`.
- `UserSettings` (1:1): `theme` (light / dark / system), `language` (uk / en), `notify_prefs` (JSON), `history_enabled`, `who_can_comment` (all / followers / nobody), `collections_visible`.
- `Follow` (етап 14): `follower` → User, generic target (User / Collection / Server), unique.
- `Badge`, `UserBadge` (етап 15).

**library**
- `Favorite`: `user`, generic target, `created_at`. Unique `(user, content_type, object_id)`.
- `Collection` (TimeStamped, Engagement частково): `owner`, `title` (≤ 80), `description` (≤ 200), `visibility` (private / link / public), `share_token` (для «за посиланням»), `is_setup`, `editors` M2M → User.
- `CollectionItem`: `collection`, generic target, `position`, `slot` (для сетапу: version / loader / pack / mod / resourcepack / shader / skin / server), `note` (≤ 140). Unique `(collection, content_type, object_id)`.
- `ViewHistory`, `Download` (етап 16; `Download` створюється вже з етапу 3 для відстеження оновлень).

**social**
- `Like`: `user`, generic target. Unique.
- `Review`: `user`, generic target, `stars` (1–5), `text` (≤ 1000, nullable), `helpful_count`, `status`. Unique `(user, target)`. Для `server` — не частіше разу на 30 днів (оновлення існуючого).
- `ReviewVote`: `user`, `review`, `is_helpful`. Unique.
- `Comment` (Publishable): `user`, generic target, `parent` (nullable, лише 1 рівень), `body` (≤ 1000), `is_pinned`.

**mods**
- `Category`: `slug`, `name_uk`, `project_type`.
- `Project` (Engagement): `modrinth_id` (unique), `slug` (unique), `project_type` (mod / resourcepack / shader), `title`, `summary` (англ. з Modrinth), `summary_uk` (від спільноти, nullable), `body_md`, `icon_url`, `gallery` (JSON), `categories` M2M, `loaders` (Array), `game_versions` (Array), `license`, `source_url`, `modrinth_downloads`, `gpu_load` (light / medium / heavy, лише шейдери), `claimed_by` (FK User, nullable), `status`, `synced_at`.
- `ProjectVersion`: `project`, `modrinth_version_id`, `version_number`, `game_versions` (Array), `loaders` (Array), `file_url`, `file_name`, `file_size`, `sha1`, `dependencies` (JSON: `[{project_id, dependency_type}]`), `released_at`. Індекс GIN на масивах.

**skins**
- `Skin` (Authored, Publishable, Engagement): `title` (≤ 60), `file` (PNG), `preview` (PNG 2D-рендер), `model` (classic / slim), `dominant_color` (hex), `color_bucket` (red / orange / yellow / green / cyan / blue / purple / pink / brown / black / white / gray), `style_tags` (Array, зі списку), `source` (upload / recolor), `parent` (FK Skin, nullable).

**servers**
- `Server` (Authored як власник, Publishable, Engagement): `name`, `slug`, `host`, `port` (25565 за замовчуванням), `edition` (java / bedrock / both), `modes` (Array), `versions_label` (рядок, напр. "1.20–1.21"), `language` (uk / multi / …), `description` (≤ 500), `banner`, `discord_url`, `website_url`, `has_whitelist`, `is_verified`, `verify_code`, `last_online_at`.
- `ServerSnapshot`: `server`, `ts`, `is_online`, `players_online`, `players_max`, `latency_ms`, `version_name`. Індекс `(server, ts)`. Зберігаємо 30 днів сирих знімків (5 хв), далі — годинні агрегати (етап 17).

**moderation**
- `Report`: `reporter`, generic target, `reason` (inappropriate / spam / stolen / scam / other), `comment`, `status` (new / accepted / rejected), `handled_by`, `handled_at`.
- `Sanction`: `user`, `type` (warning / publish_ban / ban), `until`, `reason`, `issued_by`.
- `BannedWord`: `word`, `language`.

**notifications**
- `Notification`: `user`, `type`, `payload` (JSON), `is_read`, `created_at`. Індекс `(user, is_read, created_at)`.

### 5.3 Таблиці після MVP
- **packs:** `Pack` (Authored, Publishable, Engagement: `title`, `slug`, `cover`, `summary`, `style_tags`, `game_version`, `loader`, `ram_min_gb`, `gpu_note`, `install_md`, `changelog_md`, `forked_from`), `PackItem` (`pack`, `version` → ProjectVersion, `is_required`, `added_as_dependency`).
- **moments:** `Moment` (Authored, Publishable, Engagement: `type` photo / video / embed, `caption` ≤ 140, `tags`, `embed_url`, `embed_meta` JSON, `seed`, `coords`, `world_file`, `schematic_file`, `server` FK, `pack` FK), `MomentMedia` (`moment`, `file`, `thumb`, `kind`, `width`, `height`, `duration`, `order`, `processing_status`).
- **worlds:** `World` (Authored, Publishable, Engagement: `title`, `slug`, `type` adventure / parkour / pvp / puzzle / base / other, `game_version`, `players_min`, `players_max`, `difficulty`, `play_time_min`, `file`, `schematic`, `gallery`).
- **community:** `Challenge` (`theme`, `slug`, `rules`, `starts_at`, `ends_at`, `voting_ends_at`, `winner` FK Moment), `ChallengeVote` (`user`, `challenge`, `moment`, unique per user+challenge).

---

## 6. API

Базовий шлях: `/api/v1/`. Авторизація: сесійна cookie від allauth headless (`/_allauth/browser/v1/...`), CSRF-токен у заголовку `X-CSRFToken`. Документація: `/api/docs/` (Swagger), схема: `/api/schema/`.

### Загальні правила
- Пагінація каталогів: `?page=&page_size=` (за замовчуванням 24, максимум 60). Стрічки й коментарі — cursor-пагінація.
- Сортування: `?sort=popular|new|updated|top|trend`.
- Помилки: `{"detail": str, "code": str, "fields": {field: [str]}}` — єдиний формат через `core.exceptions.handler`.
- Тротлінг (DRF scopes): `uploads` 20/год, `comments` 30/год, `reviews` 20/добу, `reports` 20/добу, `lookup` 30/хв, `anon` 120/хв.
- Об'єкти у відповідях каталогу містять поля стану для поточного користувача: `is_favorited`, `is_liked`, `my_review_stars` (null для гостя).
- Generic-дії приймають пару `{kind, id}`, де `id` — slug або числовий id згідно з kinds-реєстром.

### Ендпоінти MVP
| Метод і шлях | Опис | Етап |
| --- | --- | --- |
| `GET /health` | Перевірка БД, Redis | 0 |
| `GET/PATCH /me` | Поточний користувач | 2 |
| `GET/PATCH /me/game-profile`, `GET/PATCH /me/settings` | Налаштування гри й акаунта | 2 |
| `POST /me/onboarding` | Збереження онбордингу | 2 |
| `GET /users/{nickname}` | Публічний профіль (з урахуванням приватності) | 2 |
| `GET /users/{nickname}/works?kind=` | Створене автором | 2/5 |
| `GET /mods` | Каталог: `type, game_version, loader, category, gpu_load, q, sort` | 3 |
| `GET /mods/{slug}` | Сторінка мода | 3 |
| `GET /mods/{slug}/versions?game_version=&loader=` | Версії | 3 |
| `GET /mods/{slug}/download?game_version=&loader=` | Підбір файлу → 302 на file_url, запис `Download` | 3 |
| `POST /mods/suggest` | Запропонувати мод за посиланням Modrinth | 3 |
| `GET /categories?type=` | Категорії | 3 |
| `POST /favorites`, `DELETE /favorites` | `{kind, id}` | 4 |
| `GET /me/saved?kind=&game_version=` | Обране | 4 |
| `GET/POST /collections`, `GET/PATCH/DELETE /collections/{id}` | Колекції (`?share_token=` для доступу за посиланням) | 4 |
| `POST /collections/{id}/items`, `DELETE /collections/{id}/items/{item_id}`, `POST /collections/{id}/reorder` | Елементи | 4 |
| `POST /collections/{id}/copy` | Скопіювати собі | 4 |
| `GET /me/collections` | Мої колекції (для поповера «Додати в колекцію» — з прапорцем `contains` для `{kind,id}`) | 4 |
| `POST/DELETE /likes` | `{kind, id}` | 4 |
| `GET /reviews?kind=&id=&sort=helpful|new`, `PUT /reviews` (upsert), `DELETE /reviews/{id}` | Відгуки | 4 |
| `POST /reviews/{id}/vote` | Корисно / не корисно | 4 |
| `GET /comments?kind=&id=`, `POST /comments`, `PATCH/DELETE /comments/{id}`, `POST /comments/{id}/pin` | Коментарі | 4 |
| `GET /skins`, `POST /skins` (multipart), `GET/PATCH/DELETE /skins/{id}` | Скіни: фільтри `style, color, model, sort` | 5 |
| `GET /skins/{id}/download` | PNG + лічильник | 5 |
| `GET /skins/lookup?nickname=` | Скін гравця через Mojang | 5 |
| `GET /servers`, `POST /servers`, `GET/PATCH/DELETE /servers/{slug}` | Сервери: фільтри `mode, edition, language, version, online, whitelist` | 6 |
| `GET /servers/{slug}/stats?range=24h|7d` | Графік онлайну, аптайм | 6 |
| `POST /servers/{slug}/verify` | Перевірка коду в MOTD | 6 |
| `POST /servers/{slug}/copy-ip` | Лічильник копіювань (без авторизації, тротлінг) | 6 |
| `GET /search?q=&kind=` | Пошук, результати згруповано за kind | 7 |
| `GET /home` | Агрегат для головної (кеш 5 хв, персоналізований для авторизованих) | 7 |
| `GET /top?kind=&period=week|month|all` | Топи | 7 |
| `POST /reports` | Скарга `{kind, id, reason, comment}` | 8 |
| `GET /me/notifications`, `POST /me/notifications/read` | Сповіщення | 8 |
| `GET /me/export`, `DELETE /me` | Експорт даних, видалення акаунта | 8 |

Ендпоінти етапів 10–18 описуються в розділах відповідних етапів.

---

## 7. Фронтенд

### 7.1 Маршрути (App Router)
| Маршрут | Рендер | Примітки |
| --- | --- | --- |
| `/` | SSR | Головна |
| `/mods`, `/mods/[slug]` | SSR | Фільтри в query string |
| `/skins`, `/skins/[id]`, `/skins/lookup` | SSR / клієнт для 3D | skinview3d через `dynamic(..., { ssr: false })` |
| `/servers`, `/servers/[slug]` | SSR | Графік — власний SVG-компонент |
| `/c/[id]` | SSR | Колекція |
| `/u/[nickname]` | SSR | Профіль |
| `/top` | SSR | |
| `/me/saved`, `/me/collections`, `/me/settings`, `/me/notifications`, `/me/works` | Клієнт, захищені | |
| `/welcome` | Клієнт, захищений | Онбординг |
| `/login`, `/register`, `/password-reset` | Клієнт | |
| `/create` | Клієнт, захищений | Вибір типу → форма |
| `/rules`, `/privacy` | Статичні | |
| `/dev/ui` | Лише dev | Вітрина дизайн-системи |

Після MVP: `/packs`, `/packs/[slug]`, `/packs/new`, `/moments`, `/moments/[id]`, `/worlds`, `/worlds/[slug]`, `/challenges`, `/challenges/[slug]`, `/feed`, `/me/setup`, `/me/history`, `/me/servers/[slug]`, `/guides/[slug]`.

### 7.2 Доступ до API
- `src/lib/api/schema.d.ts` — генерується командою `make api-types`; руками не редагувати.
- `src/lib/api/client.ts` — `openapi-fetch` для браузера (`credentials: "include"`, CSRF-заголовок).
- `src/lib/api/server-client.ts` — для Server Components: базова адреса `INTERNAL_API_URL`, пересилає cookie запиту.
- Query keys — у `src/lib/query-keys.ts`, один об'єкт на домен.
- Мутації «Зберегти», «Лайк», «В колекцію» — оптимістичні з відкатом при помилці й тостом.

### 7.3 Дизайн-система (коротко; деталі — у skill `design-system`)
- Токени — CSS-змінні в `src/styles/tokens.css`, підключені в Tailwind 4 через `@theme`. Жодних «сирих» hex у компонентах.
- Теми: світла «Папір» (за замовчуванням) і темна «Ніч», `next-themes`, атрибут `data-theme`.
- Шрифти через `next/font/google`: Cormorant Garamond (заголовки, `subsets: ["latin","cyrillic"]`), Inter (текст).
- Кути: `border-radius: 0` скрізь (виняток — аватари-кола не використовуємо; аватар теж квадрат).
- Рамки 1 px, без тіней і градієнтів.
- Один головний акцент `--accent` (приглушений зелений трави).
- 3D — лише skinview3d на сторінках скіна, профілю, «Скін тижня», пошуку скіна за ніком.
- Mobile-first; брейкпоінти Tailwind за замовчуванням; на мобільних — нижня панель «Головна · Пошук · Додати · Обране».

---

## 8. Зовнішні інтеграції

### Modrinth
- База: `https://api.modrinth.com/v2`. Обов'язковий унікальний `User-Agent`, напр. `blockcraft-ua/1.0 (contact: <email з .env>)`.
- Використовуємо: `GET /search` (facets: `project_type`, `versions`, `categories`; `index=downloads`), `GET /project/{id|slug}`, `GET /project/{id}/version`, `GET /projects?ids=[...]`, `GET /tag/category`.
- Клієнт `apps/mods/clients.py`: httpx з таймаутом 10 с, 3 повтори з backoff на 5xx/429, читання заголовків rate-limit; відповіді парсяться pydantic-схемами (лише потрібні поля).
- Ми не зберігаємо файли модів — лише `file_url` з Modrinth.

### Mojang
- Нік → UUID: `GET https://api.mojang.com/users/profiles/minecraft/{nickname}`.
- UUID → профіль із текстурою: `GET https://sessionserver.mojang.com/session/minecraft/profile/{uuid}` → `properties[0].value` (base64 JSON) → `textures.SKIN.url`, `metadata.model == "slim"`.
- Кеш у Redis 10 хв (позитивний) і 2 хв (негативний, «не знайдено»). Тротлінг на нашому боці.

### Minecraft-сервери
- `mcstatus.JavaServer.async_lookup(host:port).async_status()` з таймаутом 3 с; Bedrock — `BedrockServer`.
- Задача пінгує всі опубліковані сервери кожні 5 хв пачками з обмеженням паралельності (≈ 20).
- Поточний статус — у Redis `server:status:{id}` (TTL 15 хв), знімок — у `ServerSnapshot`.
- Верифікація: власник отримує код `bc-XXXXXX`, додає його в MOTD; задача `verify_server` шукає код у `status.motd`.

### oEmbed (етап 11)
- YouTube: `https://www.youtube.com/oembed?url=...&format=json`; TikTok: `https://www.tiktok.com/oembed?url=...`. Зберігаємо `title`, `thumbnail_url`, `html` не зберігаємо — плеєр рендеримо самі за id.

---

## 9. Фонові задачі (Celery beat)

| Задача | Розклад | Етап |
| --- | --- | --- |
| `mods.sync_popular` | щодня 03:00 | 3 |
| `mods.sync_versions_for_tracked` | щодня 03:30 (моди, що є в обраному / завантаженнях / зборках) | 3 → 16 |
| `servers.ping_all` | кожні 5 хв | 6 |
| `servers.aggregate_hourly`, `servers.cleanup_snapshots` | щогодини / щодня 04:00 | 17 |
| `social.recalc_scores` | щогодини :15 | 4 |
| `social.recalc_trends` | щогодини :45 | 7 |
| `search.reindex_all` | щодня 05:00 (+ точкові оновлення через сигнали) | 7 |
| `skins.render_preview` | на подію | 5 |
| `moments.process_media` | на подію | 11 |
| `notifications.weekly_digest` | понеділок 10:00 | 15 |
| `library.flush_view_history` | кожні 10 хв | 16 |
| `community.close_challenge` | щохвилини перевіряє дедлайни | 13 |

Правила: задачі ідемпотентні; великі — пачками; кожна має тест із замоканим зовнішнім API.

**Формули рейтингу.**
- Байєсівське середнє: `score = (C·m + Σstars) / (C + n)`, де `m` — середня оцінка по kind, `C = 10`.
- Тренд: `trend = Σ(w_i · e^(−age_hours/48))`, де вага лайка = 1, збереження = 2, завантаження = 0.5, відгуку = 3; беремо події за останні 14 днів.

---

## 10. Етапи розробки

Формат етапу: **Мета** → **Задачі** (ID для PROGRESS.md) → **Готово, коли** → **Тести**. Задача вважається виконаною лише тоді, коли виконано загальне «Визначення готовності» з CLAUDE.md.

Орієнтовний час — для 1 розробника по 2–3 години на день.

### Етап 0 — Фундамент (≈ 1 тиждень)
**Мета:** порожній, але робочий скелет: `make up` піднімає все, тести й CI зелені.

- **0.1** Монорепо: `.gitignore`, `.editorconfig`, `README.md`, `.env.example` з усіма змінними розділу 11.
- **0.2** Бекенд: uv-проєкт, Django 5.2, налаштування `base/dev/test/prod` через змінні оточення, `apps/core` з `GET /api/v1/health` (перевіряє БД і Redis).
- **0.3** PostgreSQL, Redis (кеш + сесії), Celery worker + beat, тестова задача `core.ping`.
- **0.4** Фронтенд: Next.js 16 + TS strict + Tailwind 4 + ESLint + Prettier; сторінка `/` показує статус `/api/v1/health`.
- **0.5** `docker-compose.yml`: `db`, `redis`, `meili`, `backend`, `worker`, `beat`, `frontend`, `nginx` (порт 8080). Hot reload для обох частин. Альтернатива для Windows: фронтенд локально через `pnpm dev`, решта в Docker — описати в README.
- **0.6** `Makefile`: `up, down, logs, ps, sh-back, sh-front, migrate, makemigrations, createsuperuser, test, test-back, test-front, lint, fmt, typecheck, api-types, seed, sync-mods, reset-db`.
- **0.7** Тести: pytest + pytest-django + factory-boy + coverage; Vitest + Testing Library; по одному тесту на health.
- **0.8** drf-spectacular: `/api/schema/`, `/api/docs/`; `make api-types` генерує `frontend/src/lib/api/schema.d.ts`.
- **0.9** pre-commit: ruff (check + format), prettier, eslint, перевірка великих файлів і секретів.
- **0.10** GitHub Actions `ci.yml`: бекенд (ruff, pytest з Postgres і Redis як services), фронтенд (eslint, tsc --noEmit, vitest, next build).

**Готово, коли:** `make up` → http://localhost:8080 показує сторінку зі статусом «ok»; `/api/docs/` відкривається; `make test` і CI зелені; README пояснює запуск з нуля.
**Тести:** health (БД і Redis доступні / недоступні), рендер стартової сторінки.

### Етап 1 — Дизайн-система й каркас (≈ 1 тиждень)
**Мета:** усі базові компоненти й шаблони сторінок у фінальному стилі, щоб далі лише наповнювати.

- **1.1** Токени (`tokens.css`), дві теми, `next-themes`, перемикач теми, шрифти.
- **1.2** Примітиви `components/ui`: `Button` (primary / secondary / ghost, розміри), `IconButton`, `Input`, `Textarea`, `Select`, `Chip` / `FilterChip`, `Tabs`, `Card` (квадратна обкладинка + назва + метадані), `Badge`, `Dialog`, `Sheet` (мобільний), `Popover`, `Toast`, `Skeleton`, `EmptyState`, `LoadMore`, `SaveButton` (поки без логіки), `StarRating`, `Avatar` (квадрат).
- **1.3** Layout: `Header` (ліворуч навігація капслоком, по центру логотип, праворуч пошук / обране / аватар), мобільний header + `MobileTabBar`, `Footer` з дисклеймером «Не є офіційним продуктом Minecraft. Не пов'язано з Mojang або Microsoft».
- **1.4** Шаблони: `CatalogPage` (ілюстрація, заголовок, лічильник, рядок фільтрів, сітка, «показати ще»), `DetailPage` (медіа ліворуч, інформація праворуч, вкладки), `FormPage`.
- **1.5** `/dev/ui` — вітрина всіх компонентів у всіх станах (лише в dev).
- **1.6** Сторінки 404 («Тут лише пустота… як у Краю») і 500, глобальні `loading` і `error`.
- **1.7** Ілюстрації-заглушки для розділів (SVG-квадрати) з місцем під фінальні PNG/WebP.

**Готово, коли:** на `/dev/ui` усі компоненти виглядають правильно в обох темах на 375 px і 1440 px, без горизонтального скролу; навігація клавіатурою працює; Lighthouse Accessibility ≥ 90.
**Тести:** Vitest — рендер і ключова поведінка `Button`, `Tabs`, `Dialog`, `FilterChip`.

### Етап 2 — Акаунти (≈ 1,5 тижня)
**Мета:** реєстрація, вхід, онбординг, профіль, налаштування.

- **2.1** Кастомний `User` (міграція до першого `migrate` у prod!), `GameProfile`, `UserSettings` (створюються сервісом при реєстрації), адмінка.
- **2.2** allauth headless (browser client): реєстрація email + пароль, підтвердження email (dev — console backend), вхід, вихід, скидання пароля.
- **2.3** Discord і Google OAuth (ключі в `.env`, кнопки на фронтенді).
- **2.4** Фронтенд: `/login`, `/register`, `/password-reset`; хук `useMe`; захищені маршрути через middleware; модалка «Увійди, щоб не загубити» з поверненням до дії.
- **2.5** Онбординг `/welcome`: версія + лоадер (з підказкою «як дізнатися свою версію»), Java / Bedrock, інтереси; пропустити можна.
- **2.6** `/me/settings`: вкладки «Гра», «Вигляд», «Приватність», «Безпека» (зміна пароля).
- **2.7** Публічний профіль `/u/[nickname]`: аватар, нік, біо, рівень (поки 1), вкладки-заглушки; закритий профіль показує лише нік.
- **2.8** Валідація ніка (унікальність без урахування регістру, заборонені слова).

**Готово, коли:** можна зареєструватися, підтвердити пошту, пройти онбординг, змінити налаштування, увійти через Discord; гість бачить чужий відкритий профіль, а закритий — ні.
**Тести:** реєстрація й вхід (API), створення профілів при реєстрації, приватність профілю, валідація ніка; Playwright-сценарій — на етапі 9.

### Етап 3 — Моди (≈ 1,5 тижня)
**Мета:** каталог модів, ресурспаків і шейдерів із Modrinth з правильною кнопкою завантаження.

- **3.1** Моделі `Category`, `Project`, `ProjectVersion`, адмінка (редагування `summary_uk`, `gpu_load`, статусу).
- **3.2** Modrinth-клієнт + pydantic-схеми (розділ 8).
- **3.3** `mods.sync_popular`: топ-N (налаштування, за замовчуванням 300 модів, 100 ресурспаків, 100 шейдерів) для підтримуваних версій; upsert; `make sync-mods`.
- **3.4** `POST /mods/suggest`: імпорт за посиланням / slug → `pending`, після схвалення — `published`.
- **3.5** API каталогу й деталей з фільтрами; GIN-індекси на масивах версій і лоадерів.
- **3.6** Підбір файлу: найновіша версія, де `game_versions ∋ версія` і `loaders ∋ лоадер`; для ресурспаків і шейдерів лоадер ігнорується; якщо немає — 404 з поясненням і найближчими версіями. Запис `Download` для авторизованих.
- **3.7** Фронтенд: `/mods` (фільтри в URL, значення за замовчуванням з GameProfile, перемикач «показати все»), `/mods/[slug]` (галерея, опис markdown, залежності, головна кнопка, розгортка «інші версії»).
- **3.8** Плашка «Опис українською ще немає — допоможи» для модераторів (редагування в адмінці).

**Готово, коли:** після `make sync-mods` у каталозі ≥ 300 проєктів; фільтри комбінуються; «Завантажити для 1.21 · Fabric» віддає правильний файл; сторінки моду рендеряться на сервері.
**Тести:** клієнт із respx-моками (успіх, 429, 5xx), upsert ідемпотентний, підбір файлу (кілька кейсів), фільтри API.

### Етап 4 — Бібліотека й соціальне ядро (≈ 2 тижні)
**Мета:** обране, колекції, лайки, відгуки й коментарі — універсально для всіх kind.

- **4.1** `core/kinds.py`, міксини `Publishable`, `Engagement`, утиліта `resolve(kind, id)`.
- **4.2** `Favorite` + API + `/me/saved` (вкладки за kind, фільтр версії).
- **4.3** `Collection`, `CollectionItem`, видимість, `share_token`, копіювання, перестановка, редактори.
- **4.4** `Like`, `Review` (+ `ReviewVote`), `Comment` (1 рівень відповідей, закріплення автором об'єкта, `who_can_comment`).
- **4.5** Сервіси оновлюють лічильники через `F()`; `social.recalc_scores` — байєсівське середнє (розділ 9).
- **4.6** Фронтенд: `SaveButton` (оптимістичний, анімація «слота»), поповер «Додати в колекцію» (список колекцій з галочками + «Нова колекція»), `/me/saved`, `/me/collections`, `/c/[id]`, блоки «Відгуки» і «Коментарі» на сторінці мода.
- **4.7** Поля `is_favorited`, `is_liked`, `my_review_stars` у серіалізаторах без N+1 (анотації або prefetch за списком id).

**Готово, коли:** мод можна зберегти, додати в 2 колекції, оцінити з відгуком, прокоментувати й відповісти; лічильники збігаються з фактичними; приватна колекція не відкривається чужим, «за посиланням» — лише з токеном.
**Тести:** права доступу до колекцій, унікальність, лічильники, ліміт відгуку сервера (30 днів — перевіряється на етапі 6), відсутність N+1 (`django_assert_max_num_queries`).

### Етап 5 — Скіни (≈ 1,5 тижня)
**Мета:** галерея скінів із фільтрами, 3D-перегляд, завантаження власних, пошук за ніком.

- **5.1** `Skin` + сервіс завантаження: PNG, 64×64 або 64×32 (конвертувати в 64×64), ≤ 100 КБ; визначення моделі (прозорий стовпець пікселів руки → slim); домінантний колір (ігноруючи прозорі пікселі) → `color_bucket`; 2D-прев'ю (голова + тіло спереду, ×8, nearest-neighbor) у Celery.
- **5.2** API каталогу: фільтри `style`, `color`, `model`; сортування; перші 3 публікації нового автора — `pending`.
- **5.3** Фронтенд: `/skins` (палітра кольорів квадратами), `/skins/[id]` (skinview3d з анімацією ходьби, перемикач пози, fallback-зображення, «Завантажити PNG», картка «Як поставити» для Java і Bedrock, «Схожі»), форма завантаження з прев'ю в 3D до публікації.
- **5.4** `GET /skins/lookup` (Mojang, кеш) + сторінка `/skins/lookup`; кнопка «Зберегти як свій» недоступна для чужих скінів (лише перегляд і PNG).
- **5.5** Скін у профілі: користувач обирає один зі своїх скінів як «поточний» (або підтягується за `mc_nickname`).

**Готово, коли:** завантажений скін проходить перевірку, отримує прев'ю, модель і колір, після модерації з'являється в каталозі; пошук за ніком існуючого гравця показує 3D-скін.
**Тести:** валідатор (некоректний формат, розмір, 64×32), визначення slim, color bucket, Mojang-клієнт із моками (знайдено / не знайдено / 429).

### Етап 6 — Сервери (≈ 1,5 тижня)
**Мета:** каталог серверів із живим онлайном, верифікацією власника й відгуками.

- **6.1** `Server`, `ServerSnapshot`; форма додавання (валідація host / port, заборона приватних IP і localhost).
- **6.2** `servers.ping_all` (розділ 8) + статус у Redis; поля `is_online`, `players_online` у серіалізаторі беруться з Redis.
- **6.3** Верифікація через MOTD: генерація коду, кнопка «Перевірити», значок «Перевірено».
- **6.4** `GET /servers/{slug}/stats` — точки для графіка (24 год — 5-хвилинні, 7 днів — годинні середні), аптайм у %.
- **6.5** Фронтенд: `/servers` (рядки-список: назва, режими, онлайн з зеленою крапкою, «Скопіювати IP»), `/servers/[slug]` (банер, великий лічильник онлайну, графік SVG, IP, режими, Discord, відгуки з обмеженням раз на 30 днів).
- **6.6** Фільтр «зараз онлайн» і сортування за онлайном (з Redis + snapshot).

**Готово, коли:** доданий реальний сервер за кілька хвилин показує онлайн і графік; верифікація з правильним кодом проходить; відгук двічі за 30 днів оновлює попередній.
**Тести:** валідація адреси (SSRF-захист), пінг із моком mcstatus (онлайн / таймаут), верифікація, агрегація статистики.

### Етап 7 — Пошук, головна, топи (≈ 1,5 тижня)
**Мета:** пошук по всьому сайту й головна сторінка за дизайном.

- **7.1** Meilisearch: індекс `content` (поля: `kind`, `title`, `summary`, `tags`, `game_versions`, `loaders`, `color_bucket`, `modes`, `score`, `trend_score`, `published_at`); оновлення через сигнали → задача; `search.reindex_all`.
- **7.2** `GET /search` — результати згруповані за kind (по 5 на групу, `?kind=` — повний список).
- **7.3** Оверлей пошуку Ctrl+K / іконка лупи: підказки під час набору (debounce 200 мс), стрілки й Enter.
- **7.4** `GET /home`: «Для твоєї версії» (або «Популярне цього тижня»), «Скін тижня» (найвищий trend за 7 днів), «Сервери онлайн зараз» (топ-5 за онлайном), «Нове»; кеш 5 хв (персональні блоки — окремо).
- **7.5** Головна за макетом: герой із заголовком, пошуком і ілюстрацією; секції; «Скін тижня» у 3D.
- **7.6** `/top` з перемикачем розділу й періоду; `social.recalc_trends`.

**Готово, коли:** пошук знаходить «sodim» → Sodium; головна збирається < 300 мс з кешем; секції відповідають макету.
**Тести:** індексатор (документ з моделі), групування результатів, `/home` для гостя й авторизованого.

### Етап 8 — Модерація, безпека, правові сторінки (≈ 1 тиждень)
**Мета:** платформа готова до реальних користувачів.

- **8.1** `Report` + `POST /reports` + тротлінг; автоматичне приховування об'єкта після 5 незалежних скарг до розгляду.
- **8.2** Робочий процес публікацій: перші 3 публікації — `pending`; роль `trusted` після 3 схвалених; модератор схвалює / відхиляє з причиною.
- **8.3** Django admin: черга модерації (дії «Схвалити», «Відхилити»), скарги, санкції, бан.
- **8.4** Фільтр лексики (`BannedWord`, UA / RU / EN) для назв, біо, коментарів, відгуків.
- **8.5** `Notification` (результат модерації, відповідь на коментар, новий відгук на твою роботу) + дзвіночок з опитуванням раз на 60 с.
- **8.6** Безпека: CSP і безпечні заголовки в Nginx, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` у prod, обмеження розміру завантажень у Nginx і Django, перевірка MIME за вмістом, жодних приватних повідомлень.
- **8.7** Сторінки `/rules`, `/privacy`; мінімальний cookie-банер (лише необов'язкові cookie, якщо з'являться); `GET /me/export` (JSON), `DELETE /me` (анонімізація контенту або видалення — вибір користувача).

**Готово, коли:** скарга потрапляє в чергу, модератор розглядає її в адмінці, автор отримує сповіщення; заборонене слово в коментарі блокується з поясненням.
**Тести:** права модератора, автоприховування, фільтр лексики, експорт і видалення акаунта.

### Етап 9 — Реліз MVP і документація курсової (≈ 1,5 тижня)
**Мета:** робочий сайт на VPS + матеріали для пояснювальної записки.

- **9.1** `docker-compose.prod.yml`: Gunicorn (Uvicorn worker), `next build` у standalone-режимі, Nginx з TLS (certbot), без bind-mount коду, healthcheck-и, рестарт-політики.
- **9.2** Деплой на VPS: домен, HTTPS, `.env` на сервері, міграції, `collectstatic`; GitHub Actions — деплой по тегу через SSH.
- **9.3** Резервні копії: `pg_dump` щодня з ротацією 7 днів + копія `media`.
- **9.4** `make seed` — демо-дані: 20 користувачів, скіни, сервери, колекції, відгуки.
- **9.5** Playwright e2e: реєстрація → онбординг → зберегти мод → створити колекцію; завантажити скін; додати сервер.
- **9.6** Продуктивність: перевірка N+1, індекси, `next/image` для зображень, кешування `/home` і каталогів.
- **9.7** `docs/coursework/`: ER-діаграма (`graph_models`), експорт OpenAPI, UML use case (гість / гравець / автор / модератор), діаграма компонентів, скріншоти екранів, звіт покриття тестами.

**Готово, коли:** сайт доступний за HTTPS, e2e проходять у CI, бекап відновлюється на чистій машині, матеріали курсової зібрані.

---

### Етап 10 — Зборки (після MVP, ≈ 2 тижні)
- **10.1** `Pack`, `PackItem`; API CRUD, `fork`.
- **10.2** Конструктор `/packs/new`: пошук модів ліворуч, «інвентар» праворуч; перевірка сумісності за версією й лоадером; автододавання обов'язкових залежностей (позначка «додано як залежність»); попередження про конфлікти (`dependency_type == incompatible`).
- **10.3** `GET /packs/{slug}/export.mrpack`: `modrinth.index.json` (formatVersion 1, game "minecraft", dependencies: minecraft + лоадер, files з `sha1`, `downloads`, `fileSize`, `path: mods/<file>`), zip.
- **10.4** Імпорт популярних модпаків з Modrinth (`project_type=modpack`) як «офіційних» зборок.
- **10.5** Сторінки `/packs`, `/packs/[slug]` (моди сіткою іконок, вимоги, інструкція, changelog).

### Етап 11 — Моменти (≈ 2 тижні)
- **11.1** Перехід на S3-сумісне сховище (django-storages), presigned upload з браузера, `POST /moments/upload-url`.
- **11.2** `Moment`, `MomentMedia`; `moments.process_media`: фото → WebP + мініатюри; відео ≤ 60 с → MP4 (H.264) + обкладинка через ffmpeg у worker-образі.
- **11.3** Вбудовування YouTube / TikTok через oEmbed.
- **11.4** `/moments` — галерея з фільтром тегів; `/moments/[id]` — повноекранний перегляд; для постройок — сід, координати, файл світу / схематики.
- **11.5** «Момент тижня» на головній.

### Етап 12 — Світи й карти (≈ 1 тиждень)
- `World` + завантаження архіву світу (zip, ≤ 200 МБ, перевірка структури: `level.dat`), схематики (`.schem`, `.litematic`), фільтри типу, версії, кількості гравців.

### Етап 13 — Челенджі (≈ 1 тиждень)
- `Challenge`, `ChallengeVote`; участь = момент із тегом челенджу; фази «прийом робіт» → «голосування» → «результати»; переможець — на головній і з бейджем; адмін створює челенджі в адмінці.

### Етап 14 — Сетап, підписки, стрічка (≈ 1,5 тижня)
- `/me/setup` (колекція `is_setup` зі слотами), картка сетапу в профілі, «Повторити сетап».
- `Follow` (автори, колекції, сервери), `/feed` з вкладками «Для тебе» і «Підписки» (cursor-пагінація).
- «Для тебе» = нове під версію гравця + схоже на збережене (теги / категорії) + популярне в інтересах; перерахунок раз на годину, зберігання в Redis.

### Етап 15 — Рівні, бейджі, real-time сповіщення (≈ 1,5 тижня)
- XP за події (публікація схвалена, отримані лайки / збереження, корисний відгук, перемога в челенджі; без XP за перегляди), рівні за порогами, `Badge`, `UserBadge`.
- Django Channels (ASGI) + WebSocket для дзвіночка; налаштування сповіщень; тижневий email-дайджест.

### Етап 16 — Історія й відстеження оновлень (≈ 1 тиждень)
- `ViewHistory` (Redis → БД пачками, 90 днів), `/me/history`, `/me/downloads`.
- Після синхронізації Modrinth — сповіщення «вийшла нова версія» для модів і зборок з обраного / завантажень.

### Етап 17 — Кабінет власника сервера (≈ 1 тиждень)
- `/me/servers/[slug]`: графіки, копіювання IP, відгуки з відповіддю власника.
- `GET /servers/{slug}/banner.png` — банер з онлайном (Pillow, кеш 5 хв).
- Сповіщення «збережений сервер знову онлайн»; годинні агрегати й очищення сирих знімків.

### Етап 18 — Поліровка (≈ 1–2 тижні)
- OG-картинки для поширення (Next.js `opengraph-image`), QR-код посилання.
- Англійська версія інтерфейсу (next-intl), 2FA (TOTP через allauth), перефарбовувач скінів, гайди `/guides`.
- Аудит доступності, продуктивності й безпеки.

---

## 11. Змінні оточення (`.env.example`)

```
# Загальне
ENV=dev                         # dev | prod
SITE_URL=http://localhost:8080
SECRET_KEY=change-me
DEBUG=1
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:8080

# БД і кеш
POSTGRES_DB=blockcraft
POSTGRES_USER=blockcraft
POSTGRES_PASSWORD=blockcraft
DATABASE_URL=postgres://blockcraft:blockcraft@db:5432/blockcraft
REDIS_URL=redis://redis:6379/0

# Пошук
MEILI_URL=http://meili:7700
MEILI_MASTER_KEY=change-me

# Пошта
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=BlockCraft <no-reply@example.com>

# OAuth
DISCORD_CLIENT_ID=
DISCORD_CLIENT_SECRET=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# Зовнішні API
MODRINTH_USER_AGENT=blockcraft-ua/1.0 (contact: you@example.com)
MODRINTH_SYNC_LIMIT_MODS=300

# Фронтенд
NEXT_PUBLIC_SITE_URL=http://localhost:8080
INTERNAL_API_URL=http://backend:8000

# S3 (з етапу 11)
S3_ENDPOINT_URL=
S3_BUCKET=
S3_ACCESS_KEY=
S3_SECRET_KEY=
```

---

## 12. Тестування

- **Бекенд:** кожен сервіс і кожен ендпоінт має тест; зовнішні API — лише через моки (respx, monkeypatch для mcstatus); фабрики в `tests/factories.py`; ціль покриття ≥ 75 % для `apps/` до етапу 9.
- **Фронтенд:** Vitest для примітивів дизайн-системи, хуків і утиліт; Playwright для ключових сценаріїв (етап 9).
- **Правило:** баг → спочатку тест, що його відтворює, потім виправлення.

## 13. Git

- Гілка на етап: `stage-03-mods`; дрібні коміти всередині; злиття в `main` через PR після зеленого CI.
- Коміти — Conventional Commits англійською: `feat(mods): add download resolver`, `fix(skins): detect slim model`, `chore(ci): cache uv`.
- Теги релізів: `v0.9.0` = MVP.
