# BlockCraft Ukraine — технічна специфікація (v2, ребілд)

Джерело правди для коду. Що і навіщо — `docs/product.md` (прочитай на початку кожного етапу). Поточний стан — `docs/PROGRESS.md`. Факти про зовнішні API — `docs/sources.md` (з'являється в R1.2).

**Як читати.** Розділи 1–12 — довідник. Розділ 13 — етапи ребілду R0–R9. Під час задачі читай розділ свого етапу й лише ті довідкові розділи, на які він посилається.

**Позначка «v1:»** — що вже є в коді з першої версії і що з цим робити (лишити / переробити / видалити). Ребілд іде на наявному коді: працююче не переписуємо, суперечне v2 — видаляємо повністю (код, тести, роути, тексти, нова міграція видалення).

**Якщо реалізація відходить від документа** — рішення записується в `docs/PROGRESS.md` → «Журнал рішень», цей файл оновлюється в тому ж коміті. Якщо документ суперечить реальній відповіді API — правда за API: фікстура + запис у журналі + правка тут.

---

## 1. Що змінилося порівняно з v1

| Було (v1) | Стало (v2) | Чому |
| --- | --- | --- |
| Скіни завантажують гравці (PNG), модерація перших робіт | Скіни імпортуються з MineSkin і Mojang; гравець «додає в каталог» за ніком чи посиланням | Контент — лише з джерел |
| Демо-сервери `*.demo.blockcraft.test`; сервери додають лише власники | Сервери імпортуються з Modrinth Server Projects; власник підтверджує свій або додає реальний за адресою | Реальні сервери з першого дня, мова й країна з джерела |
| Збірки — етап 10 «після MVP» | Збірки + двигун сумісності — ядро; готові модпаки Modrinth — основа каталогу збірок | Головна цінність і головна технічна частина курсової |
| Лайки, коментарі, моменти, світи, челенджі, рівні, стрічка | Прибрано | Розмивали суть; «Зберегти» + оцінка + відгук достатньо |
| Статичний список версій гри (бекенд + фронтенд) | Версії з Modrinth tags | Нова версія Minecraft не вимагає релізу сайту |
| `summary_uk` редагує модератор в адмінці | Переклади пропонують гравці, модератор схвалює | «Поділився» = знання, а не файли |
| — | `/import`: папка `mods` (лише хеші з браузера) і `.mrpack` | Сценарій «чому не стартує / чи можна оновитись» |
| — | Застосунок `sources`: клієнти, реєстр джерел, журнал синхронізацій, сторінка «Звідки дані» | Прозорість агрегатора; матеріал для записки |
| — | «Моя гра» в шапці й для гостя (cookie) | Фільтр під гравця з першої секунди |

## 2. Принципи

1. **Контент — лише з джерел.** Кожен об'єкт каталогу має `source`, `external_id`, `external_url`, і UI показує джерело. Наші таблиці — дзеркало й шар поверх.
2. **Файли лишаються в джерелі.** Зберігаємо метадані й малі кеші (текстура скіна 64×64, прев'ю, обкладинка-мозаїка збірки). Завантаження — редирект на CDN джерела. Від гравців файли не приймаємо; `/import` працює з хешами й `modrinth.index.json`, які браузер дістає сам.
3. **Жодних вигаданих даних.** `make seed` (лише dev) створює демо-гравців і їхні дії поверх синхронізованих реальних даних.
4. **Зовнішні API — лише через `apps/sources/clients/`**, лише в Celery-задачах або з кешем у Redis. Кожна синхронізація пише `SyncRun`. У тестах — лише записані фікстури реальних відповідей.
5. **Сумісність детермінована й пояснювана.** Двигун повертає причину для кожного рядка («залежність Sodium Extra», «немає версії для 26.1; найближча — 1.21.11»). Тексти пояснень — на фронтенді за кодами.
6. **Одна головна дія «взяти» на екран** (product.md, розділ 3).
7. **Не тримаємо мертвий код.** Те, що v2 не потребує, видаляється разом із тестами, роутами, перекладами й полями.

## 3. Архітектура

```
Браузер ──HTTPS──> Nginx ──/            ──> Next.js (SSR + клієнт)
                         ├─/api/        ──> Django + DRF
                         ├─/_allauth/   ──> Django (allauth headless)
                         ├─/admin/      ──> Django admin
                         └─/media/      ──> кеш текстур, прев'ю, обкладинок

Next.js (сервер) ──http://backend:8000──> Django   (SSR з пересиланням cookie)
Django ──> PostgreSQL · Redis (кеш, сесії, брокер) · Meilisearch

Celery worker + beat ──> apps/sources/clients/
    ├─ Modrinth API v2  — моди, ресурспаки, шейдери, датапаки, модпаки, версії, хеші, теги
    ├─ Modrinth API v3  — сервери (Server Projects)
    ├─ MineSkin API v2  — публічна галерея скінів
    ├─ Mojang API       — скін за ніком
    ├─ Fabric/Quilt/Forge/NeoForge meta — версії лоадерів для .mrpack
    └─ Minecraft-сервери — Server List Ping (mcstatus)
```

Лишаються з v1: один origin, сесії allauth headless + CSRF, без CORS і JWT; Django — лише API й адмінка; SSR для каталогів і сторінок; мутації — TanStack Query з оптимістичним оновленням; типи API генеруються з OpenAPI; усе повільне — у Celery.

Нове:
- **Шар джерел** (`apps/sources`): HTTP-клієнти, реєстр джерел, журнал `SyncRun`. Доменні застосунки мають `importers.py` — мапінг DTO джерела в модель (upsert за `(source, external_id)`).
- **Двигун сумісності** (`apps/compat`): чисті функції без HTTP і без запису в БД; вхід — версії проєктів, вихід — `Resolution`. Викликають `mods`, `packs`, `servers`, імпорт.
- **«Моя гра»** — `{game_version, loader}` у `GameProfile` (гравець) або cookie `bc_game` (гість, формат `1.21.1:fabric`). SSR читає її й підставляє фільтри за замовчуванням.

## 4. Стек

Як у v1 (повний список — `CLAUDE.md`). Зміни:
- Бекенд: нових обов'язкових залежностей немає (`httpx`, `pydantic`, `mcstatus`, `Pillow` уже є). Розбір `modrinth.index.json` — стандартний `json`.
- Фронтенд: хеші файлів — Web Crypto (`crypto.subtle.digest("SHA-1")`), без бібліотек. Дістати `modrinth.index.json` із `.mrpack` у браузері — власний розбір центрального каталогу zip і вбудований `DecompressionStream("deflate-raw")` (R4.6), без `fflate`.
- `motion` — лише якщо справді знадобиться (у v1 так і не встановлений).
- `django-storages`, S3, Channels — не потрібні (немає файлів від гравців і real-time).

## 5. Структура репозиторію

```
blockcraft/
├── CLAUDE.md, START_HERE.md, Makefile, docker-compose*.yml, .env.example
├── docs/
│   ├── product.md         # що і навіщо
│   ├── tech.md            # цей файл
│   ├── PROGRESS.md        # трекер і журнал рішень
│   ├── sources.md         # факти про кожне джерело (R1.2)
│   ├── deploy.md          # v1, оновити в R9
│   ├── rebuild/audit.md   # аудит v1 (R0.3)
│   ├── coursework/        # матеріали записки (R9; v1 — в архіві)
│   └── archive/v1/        # специфікація, прогрес, матеріали першої версії
├── backend/apps/
│   ├── core/          # kinds, міксини (+ Sourced), пагінація, помилки, health, GameContext
│   ├── accounts/      # User, GameProfile («Моя гра»), UserSettings            v1: лишити
│   ├── sources/       # НОВЕ: clients/, registry.py, SyncRun, GameVersion, задачі метаданих
│   ├── mods/          # Project, ProjectVersion, Category, importers.py          v1: лишити, розширити
│   ├── compat/        # НОВЕ: resolver.py, rules.py, operations.py, types.py (без моделей, без HTTP); identify — у mods/identify.py
│   ├── packs/         # Pack, PackItem, PackExternalFile, LoaderRelease           v1 WIP етапу 10: доробити
│   ├── servers/       # Server, ServerSnapshot, importers.py, пінг, верифікація   v1: модель переробити
│   ├── skins/         # Skin, importers.py, обробка текстур                        v1: прибрати завантаження
│   ├── library/       # Favorite, Collection, CollectionItem, Download («взяв»)   v1: лишити
│   ├── social/        # Review, ReviewVote                                          v1: прибрати Like, Comment
│   ├── translations/  # НОВЕ: Translation
│   ├── moderation/    # Report, Sanction, BannedWord                                v1: спростити
│   ├── notifications/ # Notification                                                v1: нові типи
│   ├── search/        # Meilisearch                                                 v1: розширити
│   └── home/          # /home, /top, seed (dev)                                     v1: переробити
└── frontend/src/
    ├── app/                   # маршрути (розділ 10)
    ├── components/ui/         # примітиви (+ SourceBadge, GameChip, CompatStatus)
    ├── components/layout/
    ├── features/<name>/       # game-context, mods, compat, packs, import, servers, skins, library, profile, sources, …
    └── lib/api/               # згенерований schema.d.ts, клієнти
```

Структура Django-застосунку — як у v1: `models → services (запис) → selectors (читання) → serializers → views (тонкі)`, плюс `importers.py` для даних із джерел. HTTP-клієнтів у доменних застосунках немає — лише в `apps/sources/clients/`.

---

## 6. Модель даних

### 6.1 Спільні абстракції (`apps/core`)

**Міксини:**
- `TimeStamped`, `Authored` — як у v1.
- `Sourced` (НОВЕ) — для всього, що прийшло з джерела: `source` (TextChoices: `modrinth`, `mineskin`, `mojang`, `owner`), `external_id`, `external_url`, `synced_at`, `is_hidden` (модератор приховав у нас), `hidden_reason`. На кожній конкретній моделі — unique `(source, external_id)`. Менеджер `.visible()`.
- `Publishable` — лише для створеного гравцями: збірки спільноти, переклади. Статуси: `draft` / `pending` (лише переклади) / `published` / `rejected` / `hidden`.
- `Engagement` (скорочено): `favorites_count`, `downloads_count` (наші «взяли»), `rating_avg`, `rating_count`, `score`, `trend_score`. v1: `likes_count`, `comments_count` — видалити.

**Kinds-реєстр** (v1 `core/kinds.py` — лишити механізм, оновити таблицю):

| kind | Модель | URL-id | Відгуки | Дії |
| --- | --- | --- | --- | --- |
| `mod` | mods.Project (mod / resourcepack / shader / datapack) | slug | так | save, collect, review, report, translate, add_to_pack |
| `pack` | packs.Pack | slug | так | save, collect, review, report, translate (лише `origin=modrinth`) |
| `server` | servers.Server | slug | так | save, collect, review, report, translate (лише `source=modrinth`) |
| `skin` | skins.Skin | id | ні | save, collect, report |
| `collection` | library.Collection | id | ні | save, report |

Лічильники — лише через `core.counters.bump()` (v1). Видалення об'єкта прибирає обране, відгуки, елементи добірок (v1 `kinds.on_register`).

### 6.2 sources (НОВЕ)

- `SyncRun`: `source` (ключ `registry.py`, без choices), `job` (напр. `modrinth.catalog:shader`), `status` (running / ok / partial / failed), `started_at`, `finished_at`, `created`, `updated`, `unchanged`, `skipped`, `failed`, `errors` (JSON, до 20 прикладів з контекстом), `params` (JSON). Індекс `(source, -started_at)`. Пишеться контекст-менеджером `sync_run(source, job, params)`.
- `GameVersion`: `version` (PK, рядок), `version_type` (release / snapshot / beta / alpha), `released_at`, `is_major`, `is_supported` (показуємо в «Моїй грі» й синхронізуємо версії файлів). Підтримувані: релізи від 1.16 + `SUPPORTED_LEGACY_VERSIONS` (за замовчуванням `1.12.2,1.8.9`). Порядок — `released_at`.
- Лоадери — `Loader` TextChoices у коді (fabric, forge, neoforge, quilt + vanilla для «Моєї гри»): змінюються рідко, а від них залежать правила сумісності.

### 6.3 mods — v1: лишити, розширити

- `Category`: `slug`, `name_uk`, `project_type`, `header` (група з Modrinth). Українські назви — фікстура для всіх типів.
- `Project` (TimeStamped, Sourced[`modrinth`], Engagement): `project_type` (mod / resourcepack / shader / datapack), `slug`, `title`, `summary`, `summary_uk` + `summary_uk_by` (денормалізовано зі схваленого перекладу; `summary_uk_by` і `body_uk_html` додаються в R7.2), `body_html`, `icon_url`, `gallery`, `categories` M2M, `loaders`, `game_versions` (Array, GIN), `client_side`, `server_side`, `license`, `source_url`, `modrinth_downloads`, `modrinth_follows`, `published_at` (дата на Modrinth), `modrinth_updated_at`, `versions_synced_at` (коли читали версії; старше за `modrinth_updated_at` — версії застаріли), `gpu_load` (+ `gpu_load_manual`), `imported_by` (FK User, nullable — хто додав за посиланням). Тип `datapack` — лише проєкт, у якого всі лоадери `datapack`/`minecraft`; мод, що також є датапаком (Terralith), лишається `mod`, а у вкладці «Датапаки» каталогу показується за лоадером `datapack`. Категорій датапаків Modrinth не має — `Category` з `project_type=datapack` є копіями категорій модів. v1: `Publishable`, `status`, `claimed_by`, `suggested_by` → прибрати (імпортований з Modrinth контент уже пройшов модерацію Modrinth; приховування — `is_hidden`).
- `ProjectVersion`: `project`, `modrinth_version_id` (unique), `name`, `version_number`, `version_type`, `game_versions` (GIN), `loaders` (GIN), `date_published`, `file_url`, `file_name`, `file_size`, `sha1` (індекс), `sha512` (індекс), `dependencies` (JSON: `[{project_id, version_id, dependency_type}]` — **обов'язково з `version_id`**, якщо джерело його дає). Зберігаються версії лише для підтримуваних `GameVersion`.

### 6.4 packs — v1 WIP етапу 10: доробити

- `Pack` (TimeStamped, Engagement; v1 WIP `install_md` + `gpu_note` зливаються в `notes_md`, `style_tags` і `changelog_md` видаляються): `origin` (`modrinth` / `community`), `title`, `slug`, `summary`, `description_html`, `description_uk_html`, `icon_url` (для `modrinth`) або `cover` (згенерована мозаїка з іконок перших 4 елементів — Pillow у Celery; завантаження обкладинки гравцем прибрати), `game_version`, `loader`, `loader_version`, `items_count`, `compat_status` (ok / warnings / errors / unknown), `compat_checked_at`, `compat_report` (JSON — останній `Resolution`).
  - Для `origin=modrinth`: `external_id` (id проєкту модпака), `external_url`, `synced_at`, `modrinth_version_id`, `source_file_url`, `modrinth_downloads`, `description_html` (R4: без міксину `Sourced` — у збірок спільноти джерела немає, а `source` у ньому обов'язковий). Склад модпака — як у файлі автора (`reason=requested`, `env` з індексу), перевірка — `trust_pins` (див. 9.3).
  - Для `origin=community`: `author`, `status` (draft / published / hidden), `visibility` (private / link / public), `share_token` (16 символів), `forked_from`, `forks_count`, `ram_min_gb`, `notes_md` (поради автора).
- `PackItem`: `pack`, `project`, `version` (nullable — коли джерело прибрало файл), `reason` (requested / dependency / implicit), `required_by` (Array slug-ів), `env_client`, `env_server` (required / optional / unsupported — для `.mrpack`), `position`. Unique `(pack, project)`.
- `PackExternalFile` (для модпаків Modrinth): `pack`, `path`, `url`, `sha1`, `sha512`, `size` — файли з `modrinth.index.json`, яких немає серед проєктів Modrinth (ми їх не підбираємо й не перевіряємо, лише показуємо).
- `LoaderRelease` — як у WIP.

### 6.5 servers — v1: пінг, знімки, верифікація лишити; модель переробити

- `Server` (TimeStamped, Sourced[`modrinth` | `owner`], Engagement): `name`, `slug`, `java_host`, `java_port` (25565), `bedrock_host`, `bedrock_port` (19132), `country` (ISO 3166-1 alpha-2), `languages` (Array ISO 639-1), `categories` (Array slug-ів з Modrinth: режими й особливості; українські назви й групи — `servers/categories.py`, віддаються в `/meta`), `content_kind` (vanilla / modded), `supported_versions` (Array), `recommended_version`, `required_pack` (FK packs.Pack, nullable), `summary`, `description_html`, `description_uk_html`, `icon_url`, `banner_url` (URL з джерела; власних завантажень банера немає), `discord_url`, `website_url`, `owner` (FK User, nullable), `claimant` + `claimed_at` (останній, хто заявив сервер; код для MOTD у кожного гравця свій — HMAC від сервера й гравця), `is_verified`, `pack_chosen_by_owner` (збірку обрав власник — синхронізація її не чіпає), `last_online_at`, `modrinth_plays` (`verified_plays_2w`), `modpack_project_id` + `modpack_version_id` (модпак, який називає Modrinth; `required_pack` з нього імпортує окрема задача), `ip_copies_count`. Опис власника — `description_uk_md` → `description_uk_html` (nh3). У каталозі (`listed()`) — сервери з Modrinth і підтверджені власниками; непідтверджені бачить лише той, хто їх заявив.
  - Для `source=owner`: `external_id` — нормалізована адреса `host:port`.
- `ServerSnapshot` — як у v1 (`server`, `ts`, `is_online`, `players_online`, `players_max`, `latency_ms`, `version_name`), 30 днів сирих знімків.

### 6.6 skins — v1: обробка текстури, 3D, пошук за ніком лишити; завантаження видалити

- `Skin` (TimeStamped, Sourced[`mineskin` | `mojang`], Engagement без відгуків): `title` (назва з джерела або нік), `texture` (кеш PNG 64×64), `texture_url` (`textures.minecraft.net/…`), `texture_hash` (SHA-256 пікселів, **unique** — та сама текстура з різних джерел не дублюється, перше джерело перемагає), `model` (classic / slim), `dominant_color`, `color_bucket`, `preview` (2D PNG), `player_name` (для `mojang`), `source_views` (з MineSkin, якщо є), `added_by` (FK User, nullable). v1: `author`, `style_tags`, `parent`, `source=upload/recolor`, `status` — прибрати.
- «Мій скін» — `UserSettings.skin` (FK Skin, nullable) замість v1 `Skin.is_current`.

### 6.7 library — v1: лишити

- `Favorite`, `Collection` (`owner`, `title`, `description`, `visibility`, `share_token`, `editors`, `copied_from`, `items_count`), `CollectionItem` (без v1 `slot` — сетапу більше немає; `note` лишити).
- `Download` → узагальнити до **«взяв»**: `user`, generic target, `action` (download / export_mrpack / copy_ip / download_png), `game_version`, `loader`, `created_at`. Живить блок «Взяв» у `/me` і тренди. Гостьові дії рахуються лише в лічильниках.

### 6.8 social — v1: лишити відгуки, прибрати решту

- `Review`: `user`, generic target (mod / pack / server), `stars` (1–5), `text` (≤ 1000), `helpful_count`, `status`, `reply_text` (≤ 500), `reply_by`, `replied_at`. Відповідати може автор збірки спільноти або підтверджений власник сервера. Один відгук на гравця й об'єкт (upsert, v1).
- `ReviewVote` — як у v1.
- v1: `Like`, `Comment` — видалити (моделі, міграції видалення, API, UI, лічильники, сповіщення `reply`).

### 6.9 translations (НОВЕ)

- `Translation` (TimeStamped, Authored, Publishable): generic target (`mod`; `pack` з `origin=modrinth`; `server` з `source=modrinth`), `field` (summary / description), `text` (summary ≤ 300; description ≤ 20 000, markdown → `nh3`), `status` (pending / published / rejected / superseded), `reviewed_by`, `reviewed_at`, `reject_reason`.
- Схвалення: денормалізація в `summary_uk` / `*_uk_html` цілі + `*_uk_by`; попередній `published` → `superseded`. Один `pending` на автора + ціль + поле.

### 6.10 moderation, notifications, accounts

- **moderation** — v1 `Report`, `Sanction`, `BannedWord`. Скарга на імпортований контент → модератор ставить `is_hidden`. Премодерація — лише для перекладів; решта (збірки, добірки, відгуки) — фільтр лексики + постмодерація. v1 `core.publishing` («перші 3 роботи на модерації») і роль `trusted` — видалити, якщо після R0.4 вони більше ніде не потрібні.
- **notifications** — типи v2: `translation_published`, `translation_rejected`, `review_on_your_pack`, `review_on_your_server`, `review_reply`, `server_verified`, `pack_attention` (у збірці щось стало недоступним або з'явилися оновлення), `hidden`, `restored`, `warning`.
- **accounts** — v1. `GameProfile` = «Моя гра» (`game_version` → `GameVersion`, `loader`, `edition`). `xp`, `level`, `published_count`, `interests`, роль `trusted` — видалити (R0.4).

---

## 7. API

Базовий шлях `/api/v1/`. Загальні правила v1 лишаються: сесійна cookie allauth + `X-CSRFToken`; пагінація `?page=&page_size=` (24, макс. 60); єдиний формат помилок `{detail, code, fields}`; тротлінг DRF scopes; Swagger — `/api/docs/`.

Нове в усіх відповідях з контентом:
- `source: {name, url}` — для атрибуції;
- стан глядача: `is_favorited`, `my_review_stars` (v1 `is_liked` — прибрати);
- для типів, що залежать від гри: `fits_my_game` (bool | null) — чи є версія під «Мою гру» глядача. Для модів рахується за `game_versions` і `loaders` проєкту — тим самим правилом, що й фільтр каталогу (лоадер `vanilla` → мод із лоадером `datapack`); точний вибір файлу — двигун R3.

| Метод і шлях | Опис | Етап |
| --- | --- | --- |
| `GET /health`, `GET /csrf` | як у v1 | — |
| `GET /meta` | підтримувані версії гри, лоадери, категорії (R1); мови, країни, категорії серверів і мова каталогу за замовчуванням (`server_default_language`) — R5 | R1 |
| `GET /sources` | джерела: назва, опис, сайт, умови, остання синхронізація (статус, час, лічильники) | R1 |
| `GET/PUT/PATCH /me/game` | «Моя гра» гравця (гість — cookie `bc_game`, без ендпоінта); замінює v1 `/me/game-profile` | R1 |
| `/me`, `/me/avatar`, `/me/settings`, `/me/onboarding`, `/me/export`, `DELETE /me` | як у v1 | — |
| `GET /me/activity?section=took\|shared&page=` | «Взяв» (Download) і «Поділився» (збірки, добірки, відгуки, переклади, сервери, додані скіни) | R7 |
| `GET /mods?type=&game_version=&loader=&category=&q=&sort=&all=` | каталог; без `game_version`/`loader` — береться «Моя гра», `all=1` — без фільтра гри | R2 |
| `GET /mods/{slug}` | сторінка | R2 |
| `GET /mods/{slug}/versions?game_version=&loader=` | версії | R2 |
| `GET /mods/{slug}/similar` | схожі | R2 |
| `GET /mods/{slug}/download?game_version=&loader=&version=` | 302 на CDN + Download | R2 (v1) |
| `GET /mods/{slug}/install?game_version=&loader=` | `Resolution` для одного проєкту: файл, дерево залежностей, попередження | R3 |
| `POST /mods/import` `{url}` → 202 `{job_id}` | додати проєкт Modrinth за посиланням або slug (не модпак — `400 is_modpack`); уже є в каталозі — 200 `{slug}` | R2 |
| `GET /jobs/{id}` | стан задачі: queued / running / done / failed + `result` (напр. slug) або `error` (код); стан живе в Redis добу, id — випадковий UUID | R2 |
| `GET /categories?type=` | категорії | R2 |
| `POST /compat/resolve` `{game_version, loader, items:[{slug, version_id?}]}` | `Resolution` довільного набору (≤ 300) | R3 |
| `POST /compat/identify` `{algorithm:"sha1", files:[{hash, name}]}` | що це за файли + вгадана «гра» | R4 |
| `POST /compat/updates` `{algorithm, files, game_version, loader}` | що можна оновити й до чого | R4 |
| `GET /packs?origin=&game_version=&loader=&q=&sort=&author=&all=` | каталог збірок | R4 |
| `POST /packs`, `GET/PATCH/DELETE /packs/{slug}` | збірка спільноти (`?share_token=` для «за посиланням») | R4 |
| `POST /packs/{slug}/items` `{slug, version_id?}`, `PATCH/DELETE /packs/{slug}/items/{project_slug}` | склад; після зміни — автозалежності й перевірка | R4 |
| `GET /packs/{slug}/check` | `Resolution` збірки (кеш у `compat_report` до зміни складу) | R4 |
| `GET /packs/{slug}/retarget?game_version=&loader=` | прев'ю перенесення: kept / changed / dropped / added | R4 |
| `POST /packs/{slug}/fork` `{game_version?, loader?}` | копія, за потреби одразу під іншу гру | R4 |
| `POST /packs/{slug}/publish` `{visibility}` | з помилками сумісності — `400 pack_has_errors` | R4 |
| `GET /packs/{slug}/export.mrpack` | файл `.mrpack` + Download | R4 |
| `GET /packs/{slug}/files` | прямі посилання для ручного встановлення | R4 |
| `POST /packs/import` `{index}` або `{files:[{hash, name}], game_version?, loader?, title?}` | приватна чернетка з `modrinth.index.json` або з хешів папки `mods`; ціль — з індексу, передана або вгадана | R4 |
| `GET /servers?language=&country=&kind=&version=&category=&online=&q=&sort=` | каталог | R5 |
| `GET /servers/{slug}`, `GET /servers/{slug}/stats?range=24h\|7d` | сторінка, графік | R5 (v1) |
| `GET /servers/{slug}/join` | що потрібно для входу: версія або збірка + її статус під «Мою гру» | R5 |
| `POST /servers` `{address, edition}` | власник додає реальний сервер → чернетка + код (сервер мусить відповісти на пінг) | R5 |
| `POST/GET /servers/{slug}/verify` | перевірка коду в MOTD (v1); успіх робить гравця власником | R5 |
| `PATCH /servers/{slug}` | власник: опис українською, коротко, Discord, сайт, `required_pack`; для доданих тут — ще назва, мови, країна, версії, тип | R5 |
| `POST /servers/{slug}/copy-ip`, `GET /me/servers` | як у v1 | — |
| `GET /skins?color=&model=&source=&q=&sort=`, `GET /skins/{id}`, `/download`, `/similar` | скіни | R6 |
| `GET /skins/lookup?nickname=` | Mojang, без збереження (v1) | R6 |
| `POST /skins` `{nickname}` або `{mineskin}` (посилання чи UUID) → 202 `{job_id}` | додати скін у каталог із джерела | R6 |
| `PUT/DELETE /me/skin` `{skin_id}` | «Мій скін» | R6 |
| `/favorites`, `/me/saved`, `/collections…`, `/me/collections` | як у v1 (+ kind `pack`) | R7 |
| `GET /reviews…`, `PUT /reviews`, `DELETE /reviews/{id}`, `POST /reviews/{id}/vote`, `PUT /reviews/{id}/reply` | відгуки + відповідь автора/власника | R7 |
| `GET /translations?kind=&id=`, `POST /translations`, `POST /translations/{id}/review` `{decision, reason?}` | переклади; рішення — лише модератор | R7 |
| `POST /reports`, `/me/notifications…` | як у v1 | R7 |
| `GET /search?q=&kind=`, `GET /home`, `GET /top?kind=&period=` | + kind `pack`, фільтр «Моя гра» | R8 |

---

## 8. Джерела

Спільне для всіх клієнтів (`apps/sources/clients/base.py`): httpx з таймаутом 10 с; повтори з backoff на 5xx і помилки мережі; на 429 — пауза за `Retry-After` / `X-Ratelimit-Reset`; відповіді парсяться pydantic-схемами (лише потрібні поля; невідомі ігноруються, відсутні обов'язкові — зрозуміла помилка `SourceSchemaError`); `User-Agent` з `SOURCES_USER_AGENT` (унікальний, з контактом). Назви полів нижче — намір; правда — фікстури реальних відповідей з R1.2 і `docs/sources.md`.

### 8.1 Modrinth API v2 — `https://api.modrinth.com/v2`
- `GET /search` — facets `project_type`, `versions`, `categories`; `index=downloads|follows|updated`; `limit` ≤ 100, `offset`. Синхронізація каталогу: топ-N за завантаженнями + оновлені за останню добу.
- `GET /projects?ids=[…]`, `GET /project/{id|slug}`, `GET /project/{id}/version?loaders=&game_versions=`, `GET /versions?ids=[…]` — проєкти, версії, залежності.
- `POST /version_files` `{hashes, algorithm}` — ідентифікація файлів за хешем (`/import`, склад модпаків).
- `POST /version_files/update` `{hashes, algorithm, loaders, game_versions}` — останні сумісні версії (оновлення).
- `GET /tag/game_version`, `GET /tag/loader`, `GET /tag/category` — метадані.
- Ліміт: 300 запитів/хв на IP, однаковий з токеном і без; заголовки `X-Ratelimit-Limit/Remaining/Reset`. Токен не потрібен.
- v1: клієнт у `mods/clients.py` уже вміє повтори й rate-limit → перенести в `sources/clients/modrinth.py`.
- `.mrpack`: завантаження в `files[].downloads` — лише з `cdn.modrinth.com` (усі файли версій у фікстурах R1.2 лежать там).
- Датапаки не мають власного `project_type`: facet `project_type:datapack` працює, але проєкт приходить з `project_type: "mod"` і `datapack` в `all_project_types` — тип визначаємо самі (R2.1, `docs/sources.md`).

### 8.2 Modrinth API v3 — сервери (Server Projects, з 4 березня 2026)
- Новий тип проєкту для серверів: адреса Java (і Bedrock — поки не використовується Modrinth), країна, мова, банер, сумісність: vanilla (підтримувані й рекомендована версії) або modded (опублікований модпак Modrinth чи завантажений власний). Modrinth сам пінгує сервери й прибирає з пошуку ті, що довго недоступні.
- `GET /v3/search` з facet `project_types:minecraft_java_server` і фільтрами `minecraft_server.languages:<код>`, `minecraft_java_server.content.kind:vanilla|modpack` (facet країни не працює — фільтруємо в нас); `GET /v3/project/{id}` — повні дані сервера. Деталі — `docs/sources.md`.
- v3 документований гірше за v2 і може змінюватися: окремий клієнт `modrinth_v3.py`, схеми лише з фікстур, при зміні схеми падає задача (`SyncRun` = failed) і тест, а не сайт.
- Мапінг: vanilla → `supported_versions`, `recommended_version`; modded з модпаком Modrinth → імпорт модпака як `Pack(origin=modrinth)` → `required_pack`; modded з паком, завантаженим у сам серверний проєкт (`content.project_id` = id сервера), → теж `required_pack` з версії серверного проєкту (R1.2: це звичайна версія Modrinth з `.mrpack`). Верхньорівневі `game_versions` / `loaders` серверів ігноруємо — лише `content`.

### 8.3 MineSkin API v2 — `https://api.mineskin.org`
- `GET /v2/skins` — список публічної галереї (пагінація курсором `after`; у списку лише хеш текстури, модель і URL — у деталях), `GET /v2/skins/{uuid}` — один скін (текстура, модель, назва).
- `User-Agent` обов'язковий; `MINESKIN_API_KEY` (безкоштовний ключ з account.mineskin.org) — рекомендований для лімітів, `Authorization: Bearer`.
- Імпорт (`skins.sync_mineskin`): без назви — пропустити; текстура не 64×64 / 64×32 — пропустити; дублікат за `texture_hash` — пропустити; обробка текстури — код v1 (модель, колір, прев'ю).

### 8.4 Mojang — як у v1
- Нік → UUID → профіль із текстурою; кеш 10 хв (знайдено) / 2 хв (не знайдено); текстура лише з `textures.minecraft.net` по HTTPS; бекенд віддає data URL (без CORS у браузері). 429/5xx не кешуються.

### 8.5 Мета лоадерів — v1 WIP `packs/clients.py`
- Fabric (`meta.fabricmc.net`), Quilt (`meta.quiltmc.org`), Forge (`promotions_slim.json`), NeoForge (maven) → `LoaderRelease` для `dependencies` у `.mrpack`. Перенести в `sources/clients/loaders.py`.

### 8.6 Server List Ping — як у v1
- `mcstatus`, таймаут 3 с; SSRF-захист у два кроки (форма + резолв перед кожним пінгом); пінгуються опубліковані й ті, що чекають верифікації. Пінгуємо самі всі сервери каталогу (у т.ч. імпортовані з Modrinth) — однакова історія для графіків.

### 8.7 Правила для нового джерела
1. Спайк: реальні запити, 2–3 відповіді у `backend/apps/sources/tests/fixtures/<source>/`.
2. `docs/sources.md`: ендпоінти, поля, ліміти, умови використання, вимоги до атрибуції, ризики.
3. Клієнт у `sources/clients/`, запис у `registry.py`, задача з `sync_run(...)`, importer у доменному застосунку.
4. Сторінка `/sources` показує джерело автоматично з реєстру.

---

## 9. Двигун сумісності (`apps/compat`)

Чисті функції над даними версій. Не робить HTTP і не пише в БД; відсутні проєкти повертає списком `missing`, а викликач (сервіс) ставить задачу імпорту.

### 9.1 Вхід і правила
- `Target(game_version, loader)`, `loader` ∈ fabric / forge / neoforge / quilt / vanilla.
- `requests: [(project, pinned_version_id | None)]`.
- `rules.py` (усе, що є «знанням про Minecraft», — тут, з тестами):
  - **Які лоадери версії приймає ціль:** fabric → {fabric}; quilt → {quilt, fabric}; forge → {forge}; neoforge → {neoforge} (+ forge лише для 1.20.1); vanilla → лише файли `datapack` (мод, що постачається й датапаком, як Terralith), інакше `mod_needs_loader` (R3.1, див. журнал).
  - **Типи без лоадера-моду:** resourcepack → версії з `loaders ∩ {minecraft, vanilla}` (частина ресурспаків на Modrinth має `vanilla`); datapack → `loaders ∋ datapack`; shader → `loaders ∩ {iris, optifine, canvas, vanilla}`.
  - **Рушій шейдерів (неявна залежність):** iris на fabric / quilt / neoforge → мод `iris`; iris на forge → мод `oculus`; canvas на fabric → мод `canvas`; optifine → попередження `optifine_manual` (OptiFine немає на Modrinth); vanilla → нічого.
  - Перевірити правила на реальних даних у R3.1 і записати відхилення в журнал.

### 9.2 Вибір версії `pick_version(project, target, pinned)`
1. Кандидати: версії, де `game_versions ∋ target.game_version` і `loaders ∩ accepted(target, project_type) ≠ ∅`.
2. Якщо `pinned`: є серед кандидатів → вона; інакше — статус `pinned_incompatible`.
3. Інакше — сортування: `version_type` (release > beta > alpha), потім `date_published` ↓; перша.
4. Немає кандидатів → `no_version` + `nearest_game_versions`: до 3 найближчих (за порядком `GameVersion`) версій гри, для яких є версія з прийнятним лоадером.

### 9.3 Розв'язання `resolve(requests, target, index)` — BFS
```
queue ← запитані (reason=requested); chosen ← {}; rules_incompatible ← []
поки queue не порожня:
    (project, reason, required_by) ← queue.pop()
    якщо project у chosen: додати required_by; продовжити
    version ← pick_version(...)                 # статус ok / no_version / pinned_incompatible
    chosen[project] ← item
    для dep у version.dependencies (якщо version є):
        embedded     → пропустити
        optional     → suggestions += dep.project (якщо його немає в наборі)
        incompatible → rules_incompatible += (project, dep.project)
        required     → проєкту немає в index → missing += dep.project_id
                       інакше → якщо dep.version_id і та версія серед кандидатів — pinned=dep.version_id,
                                інакше pick + warning version_mismatch
                                queue += (dep.project, reason=dependency, required_by=project)
    неявні правила (рушій шейдерів) → queue += (..., reason=implicit)
після циклу: для кожного (a, b) у rules_incompatible: якщо b у chosen → conflict(a, b)
```
- Один проєкт — одна версія. Якщо залежність просить іншу конкретну версію, ніж уже обрана, лишаємо обрану (якщо вона серед кандидатів) і пишемо `version_mismatch`.
- Цикли не зависають (перевірка `chosen`).
- Ліміт набору — 300 проєктів (`400 pack_too_large`); готовий модпак Modrinth перевіряється без нього (до 2000).
- **`trust_pins`** (модпаки Modrinth): закріплений файл лишається, навіть якщо Modrinth позначив його для іншої гри (`pinned_other_game`), залежності не добудовуються, конфлікти — так. Автор пака вже зібрав і перевірив набір; інакше 12 із 20 топових модпаків показували б «помилки».
- **Залежності мультилоадерного файлу:** якщо файл зібрано під кілька лоадерів, а залежність не має жодного файлу для лоадера цілі (Kotlin for Forge у Fabric+NeoForge-файлі), її пропускаємо — Modrinth пише залежності на файл, а не на лоадер.
- **`incompatible` з `version_id`** забороняє лише цю версію (аддон Cobblemon проти Cobblemon 1.5), а не весь проєкт.
- Продуктивність: версії підвантажуються пачкою на кожен рівень BFS (одна вибірка `ProjectVersion` для всіх нових проєктів рівня).

### 9.4 Вихід
```
Resolution {
  status: ok | warnings | errors | incomplete
  target: {game_version, loader}
  items: [{project, version | null, reason: requested|dependency|implicit, required_by: [slug],
           status: ok | no_version | pinned_incompatible, nearest_game_versions: [..]}]
  conflicts: [{a, b, declared_by}]
  suggestions: [{project, suggested_by}]
  missing: [project_id]                     # непорожній → status = incomplete
  warnings: [{code, params}]                # version_mismatch, optifine_manual, beta_only, client_only, …
}
```
`errors` — є `no_version`, `pinned_incompatible` або `conflicts`; `warnings` — лише попередження.

### 9.5 Похідні операції
- **retarget(pack, new_target)** → `{kept, changed (стара → нова версія), dropped (no_version), added (нові залежності)}`.
- **identify(files)** → Modrinth `POST /version_files` (sha1) → `known: [(hash, name, project, version)]`, `unknown: [(hash, name)]`, `guessed_target`: найчастіша спільна версія гри й лоадер серед знайдених версій.
- **updates(files, target)** → Modrinth `POST /version_files/update` → що можна оновити й до якої версії.
- **export_mrpack(pack)** → `modrinth.index.json`: `formatVersion: 1`, `game: "minecraft"`, `versionId`, `name`, `summary`, `files: [{path, hashes: {sha1, sha512}, env: {client, server}, downloads: [url], fileSize}]`, `dependencies: {minecraft, fabric-loader | quilt-loader | forge | neoforge}`. Шляхи: `mods/`, `resourcepacks/`, `shaderpacks/`; датапаки — у `.mrpack` не входять (вони ставляться в конкретний світ) → у `/files` з інструкцією.

### 9.6 Тест-кейси (параметризовано, покриття `compat` ≥ 95 %)
1. Мод без залежностей, є реліз → ok.
2. Є лише beta → обрано beta + `beta_only`.
3. Немає версії для 26.1 → `no_version` + найближчі.
4. Required-залежність (Fabric API) додається з `reason=dependency` і `required_by`.
5. Ланцюжок A → B → C.
6. Цикл A ↔ B — без зависання.
7. A забороняє B, обидва запитані → conflict.
8. A забороняє B, B прийшов як залежність C → conflict.
9. Pinned-версія не під ціль → `pinned_incompatible`.
10. Шейдер iris: fabric → +iris; forge → +oculus; optifine → `optifine_manual`.
11. Ресурспак не залежить від лоадера гри.
12. Quilt приймає Fabric-версію; neoforge приймає forge лише на 1.20.1.
13. Залежності немає в index → `incomplete` + `missing`.
14. Мод при «Моїй грі» vanilla → `mod_needs_loader`.
15. retarget: kept / changed / dropped / added.
16. identify: відомі й невідомі хеші, вгадування цілі.
17. export: валідна схема індексу, обидва хеші, коректні шляхи, датапаки не в індексі.

---

## 10. Фронтенд

### 10.1 Маршрути
| Маршрут | Рендер | Примітки |
| --- | --- | --- |
| `/` | SSR | головна (10.4) |
| `/mods`, `/mods/[slug]` | SSR | вкладки `?type=`: моди · ресурспаки · шейдери · датапаки |
| `/packs`, `/packs/[slug]` | SSR | |
| `/packs/new`, `/packs/[slug]/edit` | клієнт, захищені | конструктор |
| `/import` | клієнт | перетягнути папку `mods` або `.mrpack`; вхід — лише для «Зберегти як збірку» |
| `/servers`, `/servers/[slug]` | SSR | |
| `/servers/add` | клієнт, захищений | власник |
| `/skins`, `/skins/[id]`, `/skins/lookup` | SSR / клієнт для 3D | skinview3d через `dynamic(..., { ssr: false })` |
| `/skins/add` | клієнт, захищений | нік або посилання MineSkin |
| `/c/[id]`, `/u/[nickname]` | SSR | |
| `/me` | клієнт, захищений | Моя гра · Взяв · Поділився |
| `/me/saved`, `/me/collections`, `/me/packs`, `/me/settings`, `/me/notifications` | клієнт, захищені | |
| `/share` | клієнт | «Поділитися»: варіанти дій |
| `/sources` | SSR | «Звідки дані» |
| `/welcome`, `/login`, `/register`, `/password-reset`, `/rules`, `/privacy`, `/dev/ui` | як у v1 | |

v1: `/skins/new`, `/create` — видалити; `/me/works` → `/me/packs` у R0.4 (збірки + сервери), `/me` з трьома блоками — R7.4.

### 10.2 «Моя гра»
- `GameChip` у шапці: «1.21.1 · Fabric ▾» → поповер: версія (з `/meta`) + лоадер; «Не знаю свою версію» → коротка підказка.
- Гравець — `PUT /me/game`; гість — cookie `bc_game` (`1.21.1:fabric`, 1 рік). Сервер читає `getGameContext()` у Server Components і передає в запити; без контексту — «популярне без фільтра» + м'яке запрошення обрати.
- Каталоги: фільтр гри за замовчуванням із контексту, перемикач «усі версії» (`all=1`) у URL. Картка, що не пасує «Моїй грі» (у пошуку, добірках), має мітку «не для 1.21.1».

### 10.3 Компоненти, які додаються до дизайн-системи
- `SourceBadge` — рядок метаданих «Modrinth ↗» (muted, зовнішнє посилання, `rel="noopener"`).
- `GameChip` — див. 10.2.
- `CompatStatus` — квадратний маркер + текст: ok (`--accent`), попередження (`--warning`, новий токен, контраст ≥ 4.5:1), помилка (`--danger`).
- `ResolutionView` — дерево «що встановити»: рядок = іконка, назва, версія, причина («потрібен для Sodium Extra»), статус; конфлікти й попередження — над списком.
- `TakeButton` — головна кнопка «взяти» з текстом, що включає «Мою гру».
- Тексти пояснень сумісності — `features/compat/copy.ts` за кодами (`no_version`, `version_mismatch`, …).

### 10.4 Головна
Герой («Збери свій Minecraft», рядок пояснення, `GameChip`, пошук) → «Популярне для 1.21.1 · Fabric» (8 модів) → «Готові збірки» (4) → смуга «Перевір свої моди» → «Сервери онлайн · українською» (5 рядків) → «Скін дня» (3D) + 6 скінів → футер з «Дані: Modrinth, MineSkin, Mojang» і дисклеймером «Не є офіційним продуктом Minecraft. Не пов'язано з Mojang або Microsoft».

### 10.5 Ключові екрани
- **Сторінка мода:** ліворуч іконка/галерея, праворуч H1, 2 рядки (українською, якщо є переклад), `TakeButton` «Завантажити для 1.21.1 · Fabric», «В збірку», «Зберегти», `SourceBadge`. Під ним — блок «Що встановити» (`ResolutionView`). Вкладки: Опис · Версії · Відгуки · Схоже.
- **Конструктор збірки:** ліворуч пошук (каталог під ціль збірки), праворуч склад, згрупований за причиною (обрані / залежності / неявні), статус перевірки зверху; «Перевірити», «Опублікувати», «Лише за посиланням». На телефоні — вкладки «Пошук · Склад».
- **`/import`:** зона перетягування (приймає папку через `webkitdirectory` і окремі `.jar`, `.mrpack`) → прогрес хешування → звіт (впізнано / невідомо / «схоже, це 1.21.1 · Fabric» / оновлення / конфлікти) → «Зберегти як збірку» / «Перевірити під іншу версію».
- **Сторінка сервера:** банер, онлайн великим числом, графік (v1 SVG), блок «Щоб зайти» (версія або збірка з `TakeButton` «Взяти збірку»), «Скопіювати IP», `SourceBadge`.
- **`/me`:** три колонки (на телефоні — секції): Моя гра (зміна), Взяв (останні 10 дій + «усе»), Поділився (лічильники й списки).

---

## 11. Фонові задачі (Celery beat)

| Задача | Розклад | Етап |
| --- | --- | --- |
| `sources.sync_game_versions` | щодня 02:30 | R1 |
| `mods.sync_catalog` (по типах: топ-N за завантаженнями; «без змін», якщо `updated` на Modrinth той самий) | щодня 03:00 | R2 |
| `mods.sync_versions` (метадані проєктів поза топом, не оновлених > 20 год, → версії лише тих, чия сторінка змінилася; `full=True` — усі) | щодня 03:30 | R2 |
| `mods.import_project` | на подію | R2 |
| `packs.sync_loader_releases` | щодня 03:45 | R4 (WIP) |
| `packs.sync_official` (топ модпаків: індекс → items через хеші) | щодня 04:00 | R4 |
| `packs.recheck` (опубліковані збірки після синхронізації → `pack_attention`) | щодня 05:00 | R4 |
| `packs.render_cover` | на подію | R4 |
| `servers.sync_modrinth` | кожні 6 год | R5 |
| `servers.ping_all` | кожні 5 хв | v1 |
| `servers.ping_server`, `servers.verify_server` | на подію | v1 |
| `servers.cleanup_snapshots` | щодня 04:30 | R5 |
| `skins.sync_mineskin` | щодня 02:00, пачками | R6 |
| `skins.import_skin` | на подію | R6 |
| `social.recalc_scores` / `social.recalc_trends` | щогодини :15 / :45 | v1 |
| `search.reindex_all` | щодня 05:30 (+ точкові через сигнали) | v1 |

Правила: задачі ідемпотентні, приймають id, великі обсяги — пачками; кожна синхронізація — через `sync_run(...)`; кожна задача має тест на фікстурах.

---

## 12. Змінні оточення (зміни до `.env.example` v1)

```
# Джерела (замінює MODRINTH_USER_AGENT і MODRINTH_SYNC_LIMIT_*)
SOURCES_USER_AGENT=blockcraft-ua/2.0 (contact: you@example.com)
SYNC_LIMIT_MOD=1000
SYNC_LIMIT_RESOURCEPACK=300
SYNC_LIMIT_SHADER=200
SYNC_LIMIT_DATAPACK=200
SYNC_LIMIT_MODPACK=200
SYNC_LIMIT_SERVERS=500
SYNC_SKINS_PER_RUN=300
SUPPORTED_LEGACY_VERSIONS=1.12.2,1.8.9
MINESKIN_API_KEY=                  # безкоштовний ключ account.mineskin.org; без нього — суворіші ліміти
```
Прибрати: `S3_*`.

---

## 13. Етапи ребілду

Формат: **Мета** → **Задачі** (ID для PROGRESS.md) → **Готово, коли** → **Тести**. Задача виконана лише тоді, коли виконано «Визначення готовності» з `CLAUDE.md`. Наприкінці кожного етапу — **продуктова перевірка**: пройти сценарії з `docs/product.md`, які зачіпає етап, на скріншотах (375 і 1440 px), і показати мені.

Гілки: `rebuild` — інтеграційна; етап — `rebuild-r<N>-<name>` від `rebuild` (не `rebuild/…`: git не дозволяє гілку `rebuild/x` поруч із `rebuild`), злиття назад після зеленого CI й рев'ю. Розмір: S — 1–2 сесії, M — 3–5, L — 6+.

### R0 — Підготовка (S)
**Мета:** зберегти зроблене, перейти на гілку ребілду, прибрати те, що суперечить v2.

- **R0.1** Закомітити незакомічені зміни етапу 10 у поточну гілку `stage-10-packs` (`wip(packs): …`), **не** включаючи `_rebuild/`. Якщо pre-commit падає через відсутні Node/pnpm — спитати мене про `--no-verify` лише для цього коміту.
- **R0.2** Гілка `rebuild` від `stage-10-packs`. Архів: `docs/tech.md`, `docs/PROGRESS.md`, `START_HERE.md`, `docs/coursework/` → `docs/archive/v1/`. Комплект: `_rebuild/CLAUDE.md` → `CLAUDE.md`, `_rebuild/START_HERE.md` → `START_HERE.md`, `_rebuild/docs/*` → `docs/`. Видалити `_rebuild/`. Коміт `docs: add v2 rebuild spec`.
- **R0.3** Аудит: підняти стек, `make test`, Playwright-скріншоти поточного UI (головна, мод, скін, сервер, збірка WIP) у `docs/archive/v1/screens-before/`. `docs/rebuild/audit.md` — таблиця «модуль / файл → лишити · переробити · видалити → етап R», з урахуванням позначок «v1:». **Зупинитися й показати мені.**
- **R0.4** Видалити за аудитом: завантаження скінів (форма, `POST/PATCH /skins`, сторінка `/skins/new`; код перевірки текстури лишити — він потрібен імпорту), лайки й коментарі (моделі → міграції видалення, API, UI, лічильники, сповіщення), демо-сервери й демо-моди в `seed`, `/create`, `/me/works`, поля й заготовки етапів 11–18 v1 (`xp`, `level`, `is_setup`, `slot` тощо). `make lint`, `make typecheck`, `make test` зелені.
- **R0.5** Оновити `.claude/`: `rules/backend.md` (+ правила джерел з `CLAUDE.md`), `rules/frontend.md` (+ атрибуція, «Моя гра», `TakeButton`), skill `design-system` (головна v2 з 10.4, нові компоненти з 10.3, токен `--warning`, нижня панель «Головна · Пошук · Поділитися · Моє», прибрати «Момент тижня» й «Челендж тижня»), skill `next-stage` (крок «продуктова перевірка» наприкінці етапу), агент `code-reviewer` (+ «контент лише з джерел», «є фікстури», «немає вигаданих даних»).

**Готово, коли:** гілка `rebuild`, документи на місці, аудит погоджено, зайве видалено, перевірки зелені.

### R1 — Шар джерел (M)
**Мета:** усі зовнішні API в одному місці, кожна синхронізація видна в журналі, версії гри — живі, «Моя гра» працює й для гостя.

- **R1.1** `apps/sources`: міксин `Sourced` (у `core`), `SyncRun` + `sync_run(...)`, `registry.py` (назва, опис українською, сайт, умови, задачі), адмінка «Синхронізації» (фільтри за джерелом і статусом), `make sync` і `make sync s=<source>` (+ `j=<job>`, `limit=N`).
- **R1.2** Спайк джерел: Modrinth v2, Modrinth v3 (сервери), MineSkin v2, Mojang — реальні запити з контейнера, 2–3 відповіді в `apps/sources/tests/fixtures/<source>/`. `docs/sources.md`: ендпоінти, поля, ліміти, умови використання й атрибуції, ризики. **Показати мені `sources.md`.**
- **R1.3** Клієнти в `sources/clients/`: перенести Modrinth (v1 `mods/clients.py`), Mojang (v1 skins), лоадери (WIP `packs/clients.py`), пінг (v1 servers); нові — `modrinth_v3.py`, `mineskin.py`. Спільна база з 8.
- **R1.4** `GameVersion` з `/tag/game_version` (`sources.sync_game_versions`), `GET /meta`; видалити статичні `GAME_VERSIONS` (бекенд) і `features/game/labels.ts` (фронтенд), профіль посилається на `GameVersion`.
- **R1.5** «Моя гра» (10.2): `GET/PUT /me/game`, cookie гостя, `getGameContext()`, `GameChip` у шапці (десктоп і телефон).
- **R1.6** Атрибуція: `source {name, url}` у серіалізаторах контенту, `SourceBadge`, `GET /sources` + сторінка `/sources`, рядок у футері.

**Готово, коли:** `make sync s=modrinth` створює `SyncRun` з лічильниками; `/sources` показує всі джерела з часом останньої синхронізації; гість змінює «Мою гру» в шапці — каталог `/mods` фільтрується під неї; у коді немає статичного списку версій.
**Тести:** клієнти на фікстурах (успіх, 429, 5xx, змінена схема → `SourceSchemaError`), `sync_run` рахує результати й ловить помилки, `/meta`, cookie-контекст у SSR-хелпері.

### R2 — Каталог Modrinth (M) — v1 `mods`: лишити, розширити
**Мета:** повний каталог моди / ресурспаки / шейдери / датапаки під «Мою гру», будь-який проєкт Modrinth додається за посиланням.

- **R2.1** `Project` за 6.3: + `datapack`, `Sourced`, `is_hidden` замість `Publishable`; `mods/importers.py` (upsert за `external_id`, ідемпотентно); `mods.sync_catalog` з лімітами по типах.
- **R2.2** `ProjectVersion` за 6.3: `version_id` у залежностях, `sha512`, `date_published`, індекси на хешах; `mods.sync_versions` лише для підтримуваних версій гри.
- **R2.3** `POST /mods/import` + `GET /jobs/{id}`: посилання / slug → задача → проєкт одразу видимий (контент уже пройшов модерацію Modrinth), `imported_by`. Модпак за посиланням → підказка «це збірка» з переходом у R4-імпорт.
- **R2.4** Українські назви категорій для всіх типів (фікстура), фільтри каталогу, `fits_my_game`.
- **R2.5** Фронтенд: `/mods` з вкладками типів і фільтрами з «Моєї гри», `/mods/[slug]` за 10.5 (поки без «Що встановити» — це R3), «Не знайшли? Додайте з Modrinth».

**Готово, коли:** після `make sync` у каталозі ≥ 1000 модів + ресурспаки, шейдери, датапаки; посилання `modrinth.com/mod/<будь-що>` додається за ≤ 30 с і знаходиться в пошуку.
**Тести:** importer (створення, оновлення, без змін, прихований не відроджується), фільтри, `fits_my_game` без N+1, import job.

### R3 — Двигун сумісності (L) — головна технічна частина
**Мета:** для будь-якого мода чи набору — точна відповідь «що встановити» з поясненнями.

- **R3.1** `apps/compat`: `types.py`, `rules.py`, `pick_version`, `resolve`, `nearest_game_versions` за розділом 9. Правила звірити з реальними даними (Iris/Oculus, Quilt/Fabric, NeoForge/Forge 1.20.1), відхилення — у журнал.
- **R3.2** Тести — усі кейси з 9.6 (параметризовано); покриття `apps/compat` ≥ 95 %.
- **R3.3** `GET /mods/{slug}/install`, `POST /compat/resolve`; `missing` → задача імпорту, відповідь `incomplete`, фронтенд опитує.
- **R3.4** Фронтенд: `ResolutionView` на сторінці мода, `TakeButton` «Завантажити для …» бере файл із `Resolution`; «Зробити збірку з цього» (передає набір у конструктор).
- **R3.5** `docs/coursework/compat.md`: постановка, псевдокод, діаграма активності (Mermaid), складність, обмеження.

**Готово, коли:** Sodium Extra під 1.21.1 · Fabric показує Sodium як залежність з причиною; шейдер з Iris під Fabric додає Iris, під Forge — Oculus; мод без версії для 26.x показує найближчі версії; збірка з конфліктом показує обидва проєкти й хто заборонив.
**Тести:** 9.6 + API (права гостя, ліміт 300, `incomplete`).

### R4 — Збірки (L) — v1 WIP етапу 10: моделі, експорт, імпорт модпаків — доробити
**Мета:** готові збірки з Modrinth + збірки спільноти, експорт `.mrpack`, перевірка, перенесення на іншу версію, імпорт папки `mods`.

- **R4.1** Моделі за 6.4 (`origin`, visibility/share_token, `compat_*`, `reason`/`required_by`, `PackExternalFile`); обкладинка-мозаїка (`packs.render_cover`) замість завантаження.
- **R4.2** Конструктор `/packs/new` і `/packs/[slug]/edit` (10.5): автозалежності з причинами, конфлікти, «Перевірити», «Опублікувати» / «Лише за посиланням».
- **R4.3** `export.mrpack` (9.5) + `GET /packs/{slug}/files`; у UI — «Як встановити» для Modrinth App, Prism Launcher, ATLauncher.
- **R4.4** `packs.sync_official`: топ модпаків Modrinth → індекс → items через `identify`; невідомі файли — `PackExternalFile`; сторінка показує джерело й «Завантажити з Modrinth».
- **R4.5** `retarget` (прев'ю) + `fork` з новою ціллю: «Зробити копію під 26.1».
- **R4.6** `/import` (10.5): Web Crypto SHA-1 у браузері → `POST /compat/identify` і `/compat/updates`; `.mrpack` → браузер дістає `modrinth.index.json` (`fflate`) → `POST /packs/import`; «Зберегти як збірку».
- **R4.7** `packs.recheck` після синхронізації; погіршився статус → `pack_attention` автору.

**Готово, коли:** збірка, зібрана на сайті, експортується в `.mrpack`, імпортується в Prism Launcher, і гра стартує (перевіряю я руками); папка `mods` з 20+ файлами розпізнається, вгадується «Моя гра»; модпак Modrinth відкривається з повним складом; копія під іншу версію показує, що випаде.
**Тести:** export (схема індексу, хеші, шляхи, датапаки окремо), import індексу, identify/updates на фікстурах, retarget diff, права (чужа збірка, `share_token`, чернетка), recheck → сповіщення.

### R5 — Сервери (M) — v1: пінг, графік, верифікація, SSRF — лишити; модель — переробити
**Мета:** лише реальні сервери; на сторінці сервера видно, що потрібно, щоб зайти, і це можна взяти.

- **R5.1** Модель за 6.5 + міграція; видалити демо-сервери й усе, що від них залежить.
- **R5.2** `servers.sync_modrinth` (8.2): спершу мова `uk`, далі популярні; vanilla → версії, modded → `required_pack` (імпорт модпака як `Pack(origin=modrinth)`).
- **R5.3** `GET /servers/{slug}/join` і блок «Щоб зайти» з `TakeButton` «Взяти збірку» або підказкою версії.
- **R5.4** Власник: `/servers/add` → пінг (сервер мусить відповісти) → код у MOTD → підтверджено → публікація; для імпортованого з Modrinth сервера той самий потік робить гравця власником; власник редагує опис українською, Discord, сайт, `required_pack` (зі своїх збірок або Modrinth).
- **R5.5** Каталог: мова (за замовчуванням «українська», якщо таких серверів ≥ 5, інакше всі), країна, vanilla / з модами, версія, «онлайн зараз», сортування за онлайном.

**Готово, коли:** у каталозі немає жодного вигаданого сервера; сервер із модпаком показує збірку, яку можна взяти; я підтверджую свій сервер кодом у MOTD.
**Тести:** importer v3 на фікстурах (vanilla / modded з паком / modded з власним паком), `join`, верифікація й права власника, SSRF (v1 тести лишаються).

### R6 — Скіни (M) — v1: обробка текстури, 3D, пошук за ніком — лишити
**Мета:** каталог реальних скінів із джерел, гравець додає скін у каталог за ніком або посиланням.

- **R6.1** Модель за 6.6 + міграція (скіни, завантажені в v1, — видалити); «Мій скін» — `UserSettings.skin`.
- **R6.2** `skins.sync_mineskin` (8.3): пачки, фільтри якості, дедуп за `texture_hash`, модель/колір/прев'ю кодом v1.
- **R6.3** `POST /skins` + `/skins/add`: нік (Mojang) або посилання / UUID MineSkin → задача → скін з `added_by`.
- **R6.4** `/skins` (колір, модель, джерело, пошук за назвою), `/skins/[id]` (3D, `TakeButton` «Завантажити PNG», «Як поставити» для Java, «Зробити моїм скіном», `SourceBadge`), `/skins/lookup`.

**Готово, коли:** у каталозі ≥ 300 скінів із MineSkin без дублікатів; скін за ніком додається в каталог і ставиться в профіль.
**Тести:** importer MineSkin на фікстурах (пропуски, дедуп), import за ніком (знайдено / не знайдено / 429), «Мій скін».

### R7 — Спільнота й кабінет (M)
**Мета:** «Поділився» має реальні дії, кабінет показує «Моя гра · Взяв · Поділився».

- **R7.1** Відгуки для mod / pack / server + `reply` автора збірки чи власника сервера; сповіщення.
- **R7.2** Переклади (6.9): форма на сторінці об'єкта, черга модератора (адмінка + кнопки на сторінці для ролі `moderator`), сповіщення, показ «Опис українською · переклав @нік» з перемикачем «оригінал».
- **R7.3** Добірки (v1) з kind `pack`; перевірити видимість і копіювання.
- **R7.4** `/me` (`GET /me/activity`), `/u/[nickname]`: збірки, добірки, відгуки, переклади, сервери, додані скіни.
- **R7.5** Модерація v2 (6.10): скарги на будь-який kind і на відгуки, `is_hidden` для імпортованого, фільтр лексики для назв збірок і добірок, відгуків, перекладів.
- **R7.6** `/share` і пункт «Поділитися» в нижній панелі.

**Готово, коли:** переклад проходить шлях «запропонував → схвалено → показано з підписом → автор отримав сповіщення»; у `/me` видно взяте й опубліковане.
**Тести:** права на `reply` і рішення щодо перекладу, `superseded`, activity без N+1, скарга → `is_hidden`.

### R8 — Пошук і головна (M) — v1: Meilisearch, оверлей Ctrl+K, `/home`, `/top` — лишити, розширити
**Мета:** пошук розуміє українські запити, головна — під «Мою гру».

- **R8.1** Індекс: + `pack`; поля `source`, `game_versions`, `loaders`, `languages` (сервери); фільтр «Моя гра»; `fits_my_game` у результатах.
- **R8.2** Українські запити: словник синонімів (`apps/search/synonyms_uk.py`: «шейдери» → shader, «оптимізація» → optimization / performance / fps, «мінікарта» → minimap, «текстури» → resourcepack …) і транслітерація кириличного запиту в латиницю як додатковий запит («содіум» → sodium).
- **R8.3** `/home` за 10.4 (гість без «Моєї гри» — популярне + запрошення обрати), `/top` з `pack`.

**Готово, коли:** «шейдери» знаходить шейдери, «содіум» — Sodium, «мінікарта» — Xaero's Minimap; головна гостя з «Моєю грою» показує лише сумісне.
**Тести:** синоніми й транслітерація, документи індексу для кожного kind, `/home` для гостя з cookie, без cookie й гравця.

### R9 — Реліз і курсова (M)
**Мета:** робочий сайт на VPS з реальними даними + матеріали пояснювальної записки.

- **R9.1** Prod під VPS 2 ГБ, на якому вже працює інший проєкт: ліміти пам'яті в `docker-compose.prod.yml` (орієнтир: Postgres 256 МБ, Redis 64 МБ, Meilisearch 256 МБ, Gunicorn 2 воркери, Celery concurrency 2, Next.js 256 МБ), swap 2 ГБ. Заміряти `docker stats` після першої синхронізації; якщо не влазить — записати цифри й рекомендувати апгрейд VPS.
- **R9.2** Деплой за `docs/deploy.md` (v1, оновити), домен, HTTPS, перша синхронізація всіх джерел на проді.
- **R9.3** Playwright e2e: С1 (мод + залежність), С2 (збірка → експорт), С3 (`/import` з фікстурними `.jar` з відомими хешами, Modrinth замокано), С4 (сервер → «щоб зайти»), С5 (скін).
- **R9.4** `make seed` (лише dev): 10 гравців, їхні збірки з реальних модів, відгуки, добірки, переклади — поверх синхронізованих даних; без джерельних даних — зрозуміла помилка «спершу `make sync`».
- **R9.5** `docs/coursework/`: ER (Mermaid, `make er-diagram` з v1), use case, компоненти, послідовність «синхронізація джерела», активність «двигун сумісності» (з R3.5), OpenAPI, звіт покриття, скріншоти (обидві теми, 1440 і 390 px), сценарій демонстрації (product.md, розділ 10).

**Готово, коли:** сайт за HTTPS із реальними даними, e2e зелені в CI, бекап відновлюється, матеріали курсової зібрані.

### Після захисту (не починати без мого рішення)
AI-чернетки перекладів (LLM + обов'язкова модерація), CurseForge (ключ; світи), NewMinecraftServers (додаткові сервери), email-сповіщення про оновлення у збережених збірках, англійська версія інтерфейсу.

---

## 14. Тестування, Git, деплой

- **Бекенд:** кожен сервіс, importer і ендпоінт має тест; зовнішні API — лише фікстури (respx, monkeypatch для mcstatus); покриття `apps/` ≥ 75 %, `apps/compat` ≥ 95 %.
- **Фронтенд:** Vitest для примітивів, хуків, `features/compat` (тексти за кодами), хешування в `/import`; Playwright — сценарії С1–С5.
- **Правило:** баг → спершу тест, що його відтворює.
- **Git:** Conventional Commits англійською, scope — застосунок (`sources`, `compat`, `packs`, …) або `docs`, `infra`. Гілки — розділ 13. Наприкінці ребілду `rebuild` → `main`, тег `v2.0.0`.
- **Деплой:** `docs/deploy.md` (v1) + R9.1. VPS спільний з іншим проєктом — будь-які зміни на сервері лише через мене.
