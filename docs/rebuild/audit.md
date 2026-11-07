# Аудит v1 перед ребілдом (R0.3)

> 2026-11-07, гілка `rebuild` (від `stage-10-packs` + WIP етапу 10).
> Рішення: **лишити** — працює й відповідає v2; **переробити** — код корисний, але модель / API / UI змінюються; **видалити** — суперечить v2.
> Скріншоти «до» — `docs/archive/v1/screens-before/` (1440 і 375 px, світла тема).

## Стан на момент аудиту

| Перевірка | Результат |
| --- | --- |
| `pytest --cov` | 480 passed, покриття 96 % (`sync_mods`, `import_modpacks` — 0 %, лише команди-обгортки) |
| Vitest | 26 файлів, 98 тестів — passed |
| `ruff check`, `eslint`, `tsc --noEmit` | чисто |
| Міграції | усі застосовані, включно з WIP `mods.0003_version_sha512` і `packs.0001_initial` |
| Дані в локальній БД | 850 проєктів Modrinth, 15 збірок (6 офіційних модпаків, 4 демо, 5 тестових чернеток), 27 скінів (усі завантажені / демо), 9 серверів (8 демо `*.demo.blockcraft.test` + «Тестовий CubeCraft» → `play.cubecraft.net`, доданий вручну), 25 користувачів |

Що видно на скріншотах (продуктово):
- **Головна** (`01-home`): «Скін тижня» й «Нове» — згенеровані `seed` однотонні скіни; «Сервери онлайн» — один реальний сервер під вигаданою назвою, решта демо офлайн. Під v2 це все «вигаданий контент».
- **Мод** (`03`, `04`): найкраща сторінка v1 — галерея, «Завантажити для 26.3 · Fabric», залежності. Але опис англійською, ціль за замовчуванням — найновіша версія, а не «Моя гра», вкладка «Коментарі».
- **Сервер** (`09`): демо-адреса, офлайн, графік порожній — сторінка нічого не дає взяти.
- **Збірка** (`11`, `12`): WIP уже вміє `.mrpack`, копію, залежності («залежність» під іконкою) — основа R4.

## Бекенд

### core
| Модуль / файл | Рішення | Етап | Примітка |
| --- | --- | --- | --- |
| `kinds.py`, `counters.py`, `exceptions.py`, `pagination.py`, `throttling.py`, `cache.py`, `health.py`, `text.py`, `schema.py` | лишити | — | механізм kinds + таблиця kinds оновлюється в R0.4 (без лайків/коментарів) і R4 (`pack`) |
| `models.py` → `TimeStamped`, `Authored`, `GenericTarget` | лишити | — | |
| `models.py` → `Engagement.likes_count`, `comments_count`, `views_count` | видалити | R0.4 | `views_count` у v2 немає (1 файл використання) |
| `models.py` → `Publishable` | переробити | R2.1, R4.1, R7.2 | лишається лише для збірок спільноти й перекладів; з `Project`, `Skin`, `Server` прибирається |
| `models.py` → міксин `Sourced` | НОВЕ | R1.1 | |
| `publishing.py` (`initial_status`, «перші 3 роботи на модерації», `published_count`) | видалити | R0.4 → остаточно після R4.1 | після видалення завантажень скінів лишаються сервери й збірки; див. питання 3 |
| `game.py` → `Loader`, `Edition` | лишити | — | |
| `game.py` → `GAME_VERSIONS` (статичний список) | видалити | R1.4 | 7 файлів (бекенд + `features/game/labels.ts`) |
| `versions.py` (`version_key`, `nearest_versions`) | лишити → перенести | R3.1 | готова основа для `nearest_game_versions`; у v2 порядок береться з `GameVersion.released_at` |
| `management/commands/er_diagram.py` | лишити | R9.5 | |

### accounts
| Модуль / поле | Рішення | Етап | Примітка |
| --- | --- | --- | --- |
| `User`, allauth headless, адаптери, валідатори, `privacy.py`, `/me`, `/me/export`, `DELETE /me`, `/me/avatar` | лишити | — | |
| `User.xp`, `User.level` | видалити | R0.4 | |
| `User.published_count` | видалити | R0.4 (якщо `publishing.py` іде) | |
| `User.Role.TRUSTED` | видалити | R0.4 | разом із `publishing.py` |
| `GameProfile.game_version` (CharField з choices) | переробити | R1.4 | FK на `GameVersion` |
| `GameProfile.interests`, `onboarding_done` | **питання 4** | — | у v2-специфікації не згадано |
| `/me/game-profile` | переробити | R1.5 | → `GET/PUT /me/game` |
| `UserSettings.who_can_comment` | видалити | R0.4 | коментарів немає |
| `UserSettings.skin` (FK) | НОВЕ | R6.1 | замість `Skin.is_current` |

### sources (НОВЕ, R1)
HTTP-клієнти зараз розкидані по чотирьох застосунках — усі переїжджають у `sources/clients/` у R1.3:
`mods/clients.py` (Modrinth v2, повтори й rate-limit — лишити логіку), `skins/mojang.py`, `packs/clients.py` (мета лоадерів), `servers/clients.py` + `servers/status.py` (пінг).

### mods
| Модуль / поле | Рішення | Етап | Примітка |
| --- | --- | --- | --- |
| `Category`, `categories.py` (українські назви) | лишити, розширити | R2.4 | + датапаки |
| `Project.modrinth_id` | переробити | R2.1 | → `Sourced.external_id` |
| `Project` ← `Publishable`, `claimed_by`, `suggested_by` | видалити | R2.1 | → `is_hidden`; `imported_by` замість `suggested_by` |
| `Project.body_md` | переробити | R2.1 | v2 зберігає лише `body_html` (+ `body_uk_html`) |
| `Project.summary_uk` (редагує модератор) | переробити | R7.2 | + `summary_uk_by` зі схваленого перекладу |
| `ProjectVersion` + WIP `sha512` | лишити, розширити | R2.2 | `released_at` → `date_published`, `version_id` у залежностях, індекс на `sha1` |
| `services.py`: `upsert_project`, `replace_versions`, `sync_*` | переробити | R2.1–R2.2 | → `mods/importers.py` + `sync_run(...)` |
| `services.py`: `import_suggested`, `publish` | переробити | R2.3 | → `POST /mods/import` + `/jobs/{id}` |
| `tasks.py`: `sync_popular`, `sync_versions_for_tracked`, `import_project` | переробити | R2.1–R2.3 | перейменування за розділом 11 tech.md |
| `markdown.py` (markdown-it + nh3) | лишити | — | знадобиться й для перекладів |
| `filters.py`, `selectors.py`, `/mods`, `/mods/{slug}`, `/versions`, `/download`, `/similar` | лишити, розширити | R2.4 | + `fits_my_game`, «Моя гра» за замовчуванням, `all=1` |
| `management/commands/sync_mods.py`, `make sync-mods` | видалити | R1.1 | → `make sync s=modrinth` |

### packs (WIP етапу 10)
| Модуль / поле | Рішення | Етап | Примітка |
| --- | --- | --- | --- |
| `Pack.is_official`, `modrinth_id` | переробити | R4.1 | → `origin` + `Sourced` |
| `Pack.cover` (завантаження гравцем), `set_cover`/`remove_cover`, `POST /packs/{slug}/cover`, `CoverField.tsx` | видалити | R4.1 | → мозаїка `packs.render_cover` |
| `Pack.style_tags`, `gpu_note`, `install_md`, `changelog_md` | **питання 5** | R4.1 | у v2 лише `notes_md` |
| `Pack.status` (Publishable) | переробити | R4.1 | + `visibility`, `share_token`, `compat_*` |
| `PackItem.is_required`, `added_as_dependency` | переробити | R4.1 | → `reason`, `required_by`, `env_client/server` |
| `PackExternalFile` | НОВЕ | R4.1 | |
| `LoaderRelease`, `store_loader_releases` | лишити | — | клієнт → `sources/clients/loaders.py` (R1.3) |
| `complete_dependencies`, `prune_dependencies`, `repick_versions`, `_pick`, `selectors.inspect`, `missing_dependency_ids` | переробити | R3.1 → R4.2 | логіка переїжджає в `apps/compat` (чисті функції); тести — джерело кейсів для 9.6 |
| `mrpack_index`, `export_mrpack` | лишити, переробити | R4.3 | + `env`, датапаки окремо, `/files` |
| `import_modpack`, `read_index`, `file_refs`, `import_popular_modpacks`, `import_modpacks` | переробити | R4.4 | → `packs.sync_official` через `identify`; невідомі файли → `PackExternalFile` |
| `fork_pack`, `recount_forks` | лишити | R4.5 | + нова ціль і `retarget` |
| `official_author` (службовий автор офіційних збірок) | видалити | R4.4 | у v2 `origin=modrinth` без автора |
| `/me/packs` | лишити | — | |

### servers
| Модуль / поле | Рішення | Етап | Примітка |
| --- | --- | --- | --- |
| Пінг, `ServerSnapshot`, `stats`, верифікація MOTD, SSRF-валідатори, `copy-ip`, `/me/servers` | лишити | — | |
| `Server.host/port/edition` | переробити | R5.1 | → `java_host/port`, `bedrock_host/port` |
| `Server.modes`, `versions_label`, `language` (одна), `has_whitelist` | переробити | R5.1 | → `categories`, `supported_versions`/`recommended_version`, `languages[]`, `country` |
| `Server.banner` (завантаження) + `POST /servers/{slug}/banner` | видалити | R5.1 | `banner_url` з джерела |
| `Server` ← `Authored`, `Publishable` | переробити | R5.1 | → `Sourced[modrinth|owner]` + `owner` |
| Демо-сервери в `seed` | видалити | R0.4 | |
| `/servers/new`, `/servers/[slug]/edit` (фронтенд) | переробити | R5.4 | → `/servers/add` + редагування власником |

### skins
| Модуль / поле | Рішення | Етап | Примітка |
| --- | --- | --- | --- |
| `textures.py` (перевірка PNG, 64×32 → 64×64, slim, колір), `render_preview` | лишити | R6.2 | переходить в імпорт |
| `mojang.py`, `GET /skins/lookup` | лишити | R1.3 | клієнт → `sources/clients/mojang.py` |
| `upload_skin`, `update_skin`, `POST/PATCH /skins`, `/skins/new`, `SkinUploadForm.tsx`, `MySkins.tsx`, `SkinOwnerActions.tsx` | видалити | R0.4 | |
| `approve`/`reject` (модерація перших робіт) | видалити | R0.4 | |
| `Skin.style_tags`, `parent`, `source=upload/recolor`, `author`, `status` | видалити | R6.1 | у R0.4 лише перестають використовуватись (зміна моделі — R6.1) |
| `Skin.is_current`, `set_current`/`clear_current`, `/me/skin` | переробити | R6.1 | → `UserSettings.skin` |
| `/me/skins` | видалити | R0.4 | «Мої роботи» без завантажень не мають сенсу |
| `styles.py` | видалити | R6.1 | стилі скінів у v2 немає |

### library
| Модуль / поле | Рішення | Етап | Примітка |
| --- | --- | --- | --- |
| `Favorite`, `Collection`, `CollectionItem`, `/favorites`, `/me/saved`, `/collections…`, копіювання | лишити | R7.3 | + kind `pack` |
| `Collection.is_setup`, `CollectionItem.slot` | видалити | R0.4 | «сетап» v1 |
| `Download` (лише `project`, `version`) | переробити | R7.4 | узагальнити до «взяв»: generic target + `action` |

### social
| Модуль / поле | Рішення | Етап | Примітка |
| --- | --- | --- | --- |
| `Like`, `like`/`unlike`, `/likes` | видалити | R0.4 | моделі → міграція видалення |
| `Comment`, `add/edit/delete_comment`, `toggle_pin`, `can_comment`, `/comments…` | видалити | R0.4 | + сповіщення `reply` |
| `Review`, `ReviewVote`, `upsert_review`, `vote_review`, `recompute_rating` | лишити | R7.1 | + `reply_text`, `reply_by`, `replied_at` |
| `recalc_scores`, `recalc_trends` | лишити | — | джерело трендів → «взяв» (R7.4) |
| `forget_target`, `recount_targets`, `signals.watch_deletions` | лишити | — | прибрати гілки лайків/коментарів у R0.4 |

### moderation, notifications
| Модуль | Рішення | Етап | Примітка |
| --- | --- | --- | --- |
| `Report`, `Sanction`, `BannedWord`, `words.py` (фільтр лексики), admin actions | лишити | R7.5 | скарга на імпортоване → `is_hidden` |
| `Report` на коментарі | видалити | R0.4 | |
| `Notification.Type`: `approved`, `rejected`, `reply`, `review` | переробити | R0.4 (`reply`), R7 (решта) | нові типи — розділ 6.10 tech.md |
| `hidden`, `restored`, `warning` | лишити | — | |

### search, home
| Модуль | Рішення | Етап | Примітка |
| --- | --- | --- | --- |
| Meilisearch-клієнт, `documents.py`, `services.py`, сигнали, `reindex_search` | лишити, розширити | R8.1 | + `pack` (у WIP уже частково), `source`, `game_versions`, `loaders` |
| `home/selectors.py`: `for_you`, `popular_packs`, `servers_online`, `top` | переробити | R8.3 | під «Мою гру» |
| `home/selectors.py`: `skin_of_week`, `new_skins`, `new_servers` | переробити | R8.3 | «Скін дня» з каталогу MineSkin |
| `home/demo.py`, `seed`: демо-скіни (згенеровані PNG), демо-сервери, `DEMO_MODS`, коментарі й лайки | видалити | R0.4 | |
| `home/demo.py`, `seed`: демо-гравці, збірки, добірки, відгуки | переробити | R9.4 | лише поверх синхронізованих даних; у R0.4 — тимчасово лишити гравців і їхні дії з реальними модами |

## Фронтенд

| Модуль / маршрут | Рішення | Етап | Примітка |
| --- | --- | --- | --- |
| `components/ui/*`, `layout/*`, `tokens.css`, теми, `/dev/ui` | лишити | — | + `SourceBadge`, `GameChip`, `CompatStatus`, `TakeButton`, `ResolutionView` (R1, R3) |
| `layout/navigation.ts`, `MobileTabBar.tsx` | переробити | R7.6 | нижня панель «Головна · Пошук · Поділитися · Моє» |
| `Footer.tsx` | переробити | R1.6 | «Дані: Modrinth, MineSkin, Mojang» |
| `features/auth`, `settings`, `notifications`, `legal`, `/login`, `/register`, `/password-reset`, `/welcome` | лишити | — | `settings/PrivacyPanel` — прибрати `who_can_comment` (R0.4) |
| `features/onboarding` | лишити | — | залежить від питання 4 |
| `features/game/labels.ts`, `GameProfileFields.tsx` | переробити | R1.4–R1.5 | версії з `/meta`; `GameChip` |
| `features/mods/*`, `/mods`, `/mods/[slug]` | лишити, переробити | R2.5, R3.4 | вкладки типів, «Моя гра», `ResolutionView`; `TranslationBanner` → R7.2 |
| `features/packs/*`, `/packs…` | переробити | R4 | `CoverField.tsx` — видалити (R4.1) |
| `features/servers/*`, `/servers…` | переробити | R5 | графік `OnlineChart`/`chart.ts`, `CopyAddress` — лишити |
| `features/skins/SkinUploadForm.tsx`, `/skins/new`, `MySkins.tsx`, `SkinOwnerActions.tsx` | видалити | R0.4 | |
| `features/skins/SkinViewer3D`, `SkinLookup`, `HowToInstall`, `texture.ts`, каталог | лишити | R6.4 | |
| `features/library/LikeButton.tsx` | видалити | R0.4 | |
| `features/social/Comments.tsx` | видалити | R0.4 | |
| `features/social/Reviews.tsx` | лишити | R7.1 | + відповідь автора |
| `features/search/*`, оверлей Ctrl+K | лишити | R8 | |
| `features/home/*`, `/top` | переробити | R8.3 | |
| `features/profile`, `/u/[nickname]`, `/c/[id]` | лишити, переробити | R7.4 | |
| `/create` | видалити | R0.4 | → `/share` (R7.6) |
| `/me/works` | видалити | R0.4 | див. питання 2 |
| `e2e/` (Playwright: реєстрація, добірки, скіни, сервери) | переробити | R0.4 (прибрати сценарії завантаження скіна й демо-серверів), R9.3 | |

## Документи й інфраструктура
| Що | Рішення | Етап |
| --- | --- | --- |
| `README.md` — посилання на `docs/coursework/`, `make sync-mods` | переробити | R0.5 (посилання), R1.1 (команди) |
| `Makefile`: `sync-mods` → `sync s=…` | переробити | R1.1 |
| `.env.example`: `MODRINTH_*`, `S3_*` → змінні з розділу 12 | переробити | R1.1–R1.3 |
| `.claude/` (rules, skills, code-reviewer) + незакомічена зміна `settings.json` | переробити | R0.5 |
| `docs/deploy.md` | лишити | R9.2 |
| pre-commit-хук не встановлений у `.git/hooks` | **питання 6** | — |

## Питання й розбіжності зі специфікацією

1. **Порожні розділи після R0.4.** Після видалення завантажень і демо в `/skins` і `/servers` до R5/R6 лишиться 0 скінів і 1 сервер. Пропоную показувати порожні стани (вони є в v1) і нічого тимчасового не додавати — це прямо вимагає CLAUDE.md.
2. **`/me/works` → куди?** tech.md каже «→ `/me` + `/me/packs`», але сторінок `/me` і `/me/packs` на фронтенді ще немає (лише API `/me/packs`). Пропоную в R0.4 перейменувати `/me/works` у `/me/packs` (там лишаються збірки й сервери — їх v1 уже показує), а `/me` з трьома блоками — у R7.4.
3. **`publishing.py` і роль `trusted`.** Після R0.4 «перші 3 роботи на модерації» лишаться для серверів і збірок v1. Пропоную видалити вже в R0.4: сервери все одно проходять верифікацію MOTD, а збірки в v2 — постмодерація (6.10).
4. **`GameProfile.interests` + онбординг «інтереси».** У v2 не згадано. Пропоную лишити онбординг як вибір «Моєї гри» (R1.5), а `interests` видалити в R0.4. Чи вони вам потрібні?
5. **Поля збірки `style_tags`, `gpu_note`, `install_md`, `changelog_md`.** У 6.4 їх немає, є лише `notes_md` і `ram_min_gb`. Пропоную в R4.1 злити `install_md` + `gpu_note` у `notes_md`, а `style_tags` і `changelog_md` видалити.
6. **Pre-commit.** Хук не встановлено, тож ruff/gitleaks при коміті не запускаються. Без Node на хості фронтенд-хуки впадуть. Пропоную `pre-commit install` і перевести prettier/eslint-хуки на `docker compose exec frontend …` (R0.5).
7. **Міграція `packs.0001_initial`** ще ніде, крім локальної БД, не застосована (етап 10 не випускався). Правило — не міняти застосовані міграції, тож у R4.1 роблю нові міграції поверх неї, без переписування 0001.
8. **«Тестовий CubeCraft».** У локальній БД є реальний сервер під вигаданою назвою (доданий вручну, не через `seed`). У R0.4 видаляю його разом із демо, бо в R5.2 реальні сервери прийдуть з Modrinth.
