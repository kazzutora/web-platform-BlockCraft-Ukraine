# Джерела контенту — факти

Що насправді повертають зовнішні API. Записано спайком R1.2 (2026-11-07) реальними запитами з контейнера `backend`. **Правда — фікстури** в `backend/apps/sources/tests/fixtures/<source>/`. У кожній теці є `_requests.json`: запит, статус, заголовки, час запису. Якщо список у відповіді обрізано до кількох реальних елементів, там це позначено.

Коли код читає поле, якого тут немає, спершу запиши фікстуру й додай поле сюди (CLAUDE.md, «Правила — джерела контенту»).

Зміст: [Modrinth v2](#modrinth-api-v2) · [Modrinth v3 — сервери](#modrinth-api-v3--сервери) · [MineSkin v2](#mineskin-api-v2) · [Mojang](#mojang) · [Мета лоадерів](#мета-лоадерів) · [Що це змінює в tech.md](#що-це-змінює-в-techmd)

---

## Modrinth API v2

`https://api.modrinth.com/v2` · фікстури `modrinth/`

### Умови
- **Ліміт:** «300 requests per minute» на IP, однаковий із токеном і без. Заголовки `X-Ratelimit-Limit` / `X-Ratelimit-Remaining` / `X-Ratelimit-Reset` (бачимо `300` / `299` / `0`). Для більшого ліміту — лист на support@modrinth.com.
- **User-Agent:** «you **must** provide a uniquely-identifying `User-Agent`». Найкращий формат — `github_username/project_name/1.56.0 (contact@…)`. Контакт рекомендований. Загальні UA ризикують блокуванням. Значення — `SOURCES_USER_AGENT` з `.env`.
- **Токен** для читання не потрібен.
- **Terms of Use** (https://modrinth.com/legal/terms, редакція від 13.08.2026), розділ «API Usage»: «limited, non-exclusive … revocable license to download, display, query … the User Generated Content on the Service via their own services, such as their websites». Окремої вимоги атрибуції немає. Ми все одно показуємо `SourceBadge` і посилання на сторінку проєкту.
- **Заборонено:**
  - використовувати назву й логотип Modrinth як свої марки. Текстове посилання «Modrinth ↗» — це не логотип;
  - натякати на партнерство чи схвалення;
  - вбудовувати сторінки Modrinth у фрейм.
- **Зміни API:** при несумісній зміні номер версії в шляху збільшується. Застарілі версії згодом повертають `410`.

### Ендпоінти, які використовуємо

| Запит | Фікстура | Що читаємо |
| --- | --- | --- |
| `GET /search?facets=[["project_type:<t>"],["versions:<v>"]]&index=downloads&limit=&offset=` | `search_{mod,shader,resourcepack,datapack,modpack}.json` | `hits[].project_id`, `project_type`, `all_project_types`, `slug`, `title`, `description`, `categories`, `versions`, `downloads`, `follows`, `icon_url`, `date_modified`, `latest_version`; `total_hits`, `offset`, `limit` |
| `GET /project/{id\|slug}` | `project_sodium.json`, `project_modpack.json` | `id`, `slug`, `project_type`, `title`, `description`, `body`, `categories`, `additional_categories`, `loaders`, `game_versions`, `versions`, `icon_url`, `gallery[] {url, featured, title, ordering}`, `license {id, name}`, `source_url`, `issues_url`, `wiki_url`, `discord_url`, `downloads`, `followers`, `published`, `updated`, `client_side`, `server_side`, `team` |
| `GET /project/{id}` неіснуючого | `project_not_found.json` | **404 з порожнім тілом** |
| `GET /projects?ids=[…]` | `projects_by_ids.json`, `projects_by_slugs.json` | список у тому ж форматі, що й `/project`; у `ids` можна передавати й slug (`["iris","oculus"]` → обидва проєкти) — так імпортуються рушії шейдерів (R3) |
| `GET /project/{id}/version?loaders=[…]&game_versions=[…]` | `project_versions_{sodium,sodium_extra,complementary,modpack}.json` | `id`, `project_id`, `name`, `version_number`, `version_type`, `game_versions`, `loaders`, `date_published`, `status`, `changelog` (markdown або null), `files[] {url, filename, primary, size, file_type, hashes {sha1, sha512}}`, `dependencies[] {project_id, version_id, file_name, dependency_type}` |
| `GET /versions?ids=[…]` | `versions_by_ids.json` | як вище |
| `POST /version_files` `{hashes, algorithm:"sha1"}` | `version_files_sha1.json` | об'єкт **хеш → версія**; невідомий хеш просто відсутній у відповіді |
| `POST /version_files/update` `{hashes, algorithm, loaders, game_versions}` | `version_files_update.json` | хеш → найновіша сумісна версія; невідомий хеш відсутній |
| `GET /tag/game_version` | `tag_game_version.json` | 922 записи `{version, version_type: release\|snapshot\|beta\|alpha, date, major}`, від найновішої; 103 релізи, з них 40 від 1.16 |
| `GET /tag/loader` | `tag_loader.json` | `{name, supported_project_types, icon}`; серед 29 лоадерів є також `datapack`, `iris`, `optifine`, `minecraft`, плагінні |
| `GET /tag/category` | `tag_category.json` | 126 записів `{name, project_type, header, icon}`; `project_type` ∈ `mod, modpack, resourcepack, shader, minecraft_java_server` |

### Важливі спостереження
- **Датапаки не мають свого `project_type`.** Facet `project_type:datapack` у пошуку працює. Але знайдені проєкти мають `project_type: "mod"`, а `datapack` стоїть лише в `all_project_types` і `categories`. Приклад: Terralith — `["datapack","mod"]`, VeinMiner — `["datapack","mod","plugin"]`. Окремих категорій для датапаків немає, вони беруть категорії модів.
- **Залежності** звичайного мода мають `version_id: null` (Sodium Extra → Sodium `required`, Iris `optional`). У модпаків залежності `embedded` з конкретним `version_id`.
- **Шейдери:** `loaders: ["iris","optifine"]`, файл `.zip`, залежностей немає. Тобто «шейдеру на Fabric потрібен Iris» (С1) у даних Modrinth **не записано** — це правило двигуна (9.1).
- **Модпак:** у версії кілька файлів — `primary` `.mrpack` і додатковий `cosign-bundle.zip`. Беремо лише `primary`.
- **Усі файли** в записаних версіях лежать на `https://cdn.modrinth.com/data/…`.
- **Категорії шейдерів** з header `performance impact`: `potato`, `low`, `medium`, `high`, `screenshot`. На них спирається фільтр «легкі» (С1).
- **Синхронізацію версій гри** проводимо через `/tag/game_version`: «підтримувані» — це релізи від 1.16 + `SUPPORTED_LEGACY_VERSIONS`. `major` = true у 103 записах — ознака великого релізу; зберігаємо її як `GameVersion.is_major`, але «підтримувана» визначається окремо.

### Ризики
- Terms кажуть «personal, non-commercial use only» про сам сервіс, а API License дозволяє «display … via their own services». BlockCraft некомерційний, тож це сумісно. Комерційне використання треба буде погоджувати з Modrinth.
- Іконки й галерею ми показуємо з `cdn.modrinth.com`. Це контент авторів, і API License дозволяє його показувати. Сторінки Modrinth у фрейм не вбудовуємо.

---

## Modrinth API v3 — сервери

`https://api.modrinth.com/v3` · фікстури `modrinth_v3/`

На https://docs.modrinth.com/api/ документовано лише v2. **v3 офіційно не описаний**: схему беремо тільки з фікстур, клієнт окремий (`modrinth_v3.py`). Ліміти й заголовки — як у v2: `300` на хвилину, ті самі `X-Ratelimit-*`.

### Пошук серверів: `GET /v3/search`
Фікстури `search_servers.json`, `search_servers_uk.json`, `search_servers_vanilla.json`.

| Facet | Працює? |
| --- | --- |
| `project_types:minecraft_java_server` (множина `types`!) | так, 2408 серверів |
| `project_type:minecraft_java_server` | ні, 0 |
| `minecraft_server.languages:uk` | так, 83 сервери |
| `minecraft_java_server.content.kind:vanilla` / `:modpack` | так, 1863 / решта |
| `minecraft_server.region:europe` | так, 1019 |
| `minecraft_server.country:US` | **ні**, 0, хоча в `hits` є `country: "US"` — країну фільтруємо в нас |
| `languages:`, `country:`, `content_kind:` без префікса | ні |

Відповідь: `hits`, `page`, `hits_per_page`, `total_hits`. Тобто сторінки тут нумеровані (`page`), а не задаються через `offset`, як у v2. Параметри `limit` і `offset` у запиті працюють.

Поля `hits[]`:
- **ідентифікація й опис:** `project_id`, `slug`, `name`, `summary`, `categories`, `icon_url`, `featured_gallery`, `gallery`, `downloads`, `follows`, `date_created`, `date_modified`;
- **`minecraft_server`:** `{max_players, country, region, languages[], active_version}`;
- **`minecraft_java_server`:** `{address, content, ping, verified_plays_2w, verified_plays_4w}`;
- **`minecraft_bedrock_server`:** `{address}`, у записаних даних — порожній рядок.

Один хіт важить 3–66 КБ, бо містить `dependencies` (до 122 елементів) і `gallery`. Тому `limit` для пошуку варто брати невеликий.

### Сервер: `GET /v3/project/{id}`
Фікстури `project_server_{1,2,3,uk,vanilla,external_pack}.json`.
- **Поля:** `id`, `slug`, `name`, `summary`, `description` (markdown), `categories`, `link_urls {discord|site|store|wiki: {platform, url, donation}}`, `gallery[] {url, featured, name, ordering}`, `icon_url`, `published`, `updated`, `status`, `games` (`["minecraft-java","minecraft-bedrock"]`).
- **`minecraft_java_server.content` має два варіанти:**
  - `{"kind":"vanilla","supported_game_versions":["26.2"],"recommended_game_version":"26.2"}`;
  - `{"kind":"modpack","project_id","version_id","project_name","project_icon"}`:
    - якщо `project_id` збігається з `id` сервера, **модпак завантажено прямо в проєкт сервера** (усі 5 у топі пошуку такі);
    - якщо `project_id` інший, сервер посилається на окремий модпак (`project_server_external_pack.json`: Rosedalean SMP → `shAGUyEd`).
- **`minecraft_java_server.ping`:** `{when, address, data {latency {secs,nanos}, version_name, version_protocol, description, players_online, players_max}}`. Modrinth сам пінгує сервери, `version_name` — це проксі, наприклад `Velocity 1.7.2-26.1.2`.
- Верхньорівневі **`game_versions` і `loaders` для серверів не надійні**: у vanilla-сервера з `recommended_game_version: "26.2"` стоїть `game_versions: ["1.21.1"]` і `loaders: ["mrpack"]`. Беремо лише `content`.
- **Мови:** коди ISO 639-1 (`en`, `uk`, `fr`, `zh`, …). Країна — ISO alpha-2 або часто `null`. `region` ∈ `europe`, `us_east`, `asia`, ….
- **Категорії серверів** беремо з `/v2/tag/category` (`project_type: minecraft_java_server`). Заголовки груп: `minecraft_server_community`, `minecraft_server_features`, `minecraft_server_gameplay`, `minecraft_server_meta`.

### Ризики
- Схема v3 може змінитися без попередження. Тоді має впасти задача (`SyncRun` = failed) і тест, але не сайт.
- Модпак, завантажений у проєкт сервера, — це версія самого серверного проєкту. Імпортувати її як `Pack(origin=modrinth)` можна через `GET /v2/version/{version_id}`, але цю фікстуру треба записати в R5.2.

---

## MineSkin API v2

`https://api.mineskin.org` · фікстури `mineskin/`

### Умови
- Документація (https://docs.mineskin.org/docs/guides/getting-started): «To use the MineSkin API you will need to create an account and obtain an API key». Ключ передається як `Authorization: Bearer msk_…`.
- **Без ключа** `GET /v2/skins` і `GET /v2/skins/{uuid}` працюють, але кожна відповідь містить попередження `{"code":"no_api_key","message":"No API Key provided"}`. Числових лімітів для читання документація не дає. 429 і `X-RateLimit-*` описано лише для генерації скінів, яку ми не використовуємо.
- Відповіді мають `Cache-Control: public, max-age=3600`.
- **Умов використання й вимог атрибуції на сторінці документації немає.** Показуємо джерело «MineSkin ↗» з посиланням на скін. ⚠ Перед R6.2 бажано отримати безкоштовний ключ і перечитати умови в кабінеті.

### Ендпоінти
| Запит | Фікстура | Що читаємо |
| --- | --- | --- |
| `GET /v2/skins?size=N` | `skins_list.json` | `skins[] {uuid, shortId, name (часто null), texture (хеш), timestamp}`; `pagination.next.after`; `links.next` |
| `GET /v2/skins?size=N&after=<uuid>` | `skins_list_next.json` | наступна сторінка — **пагінація курсором `after`** |
| `GET /v2/skins/{uuid}` | `skin.json` | `skin {uuid, shortId, name, visibility, variant: classic\|slim, texture {data {value, signature}, hash {skin, cape}, url {skin}}, tags[], views, duplicate}` |
| `GET /v2/skins/{uuid}` неіснуючого | `skin_not_found.json` | 404, `success: false`, `errors[{code:"skin_not_found"}]` |

### Спостереження
- У списку **немає моделі (`variant`) і URL текстури** — лише хеш. Модель і URL — тільки з `/v2/skins/{uuid}`. Отже, імпорт R6.2 робить один запит на кожен скін або будує URL `https://textures.minecraft.net/texture/<hash>` з хеша. Модель тоді визначаємо з текстури, як у v1.
- `url.skin` веде на `textures.minecraft.net`, той самий дозволений хост, що й у Mojang.
- Галерея — це потік щойно згенерованих скінів, багато з них без назви (`name: null`) або з технічними назвами на кшталт `archmc-d5ecda4`. Імпорт мусить відсіювати такі скіни (8.3: без назви — пропустити).

---

## Mojang

Фікстури `mojang/` · як у v1 (`skins/mojang.py` → `sources/clients/mojang.py` у R1.3)

| Запит | Фікстура | Що читаємо |
| --- | --- | --- |
| `GET https://api.mojang.com/users/profiles/minecraft/{nick}` | `profile_by_name.json` | `{id (UUID без дефісів), name}` |
| те саме, нік не існує | `profile_by_name_not_found.json` | **404** `{path, errorMessage}` |
| `GET https://sessionserver.mojang.com/session/minecraft/profile/{uuid}` | `session_profile.json` | `{id, name, properties[{name:"textures", value: base64}]}`; у `value` — JSON `textures.SKIN {url, metadata.model?}` |

- `Cache-Control: max-age=300`. Ключ не потрібен.
- Текстуру завантажуємо лише з `textures.minecraft.net` (у `value` вона приходить як `http://…`, ми міняємо схему на `https`). Фікстуру з PNG-текстурою реального гравця не зберігаємо: тести обробки текстур малюють зображення самі.
- ⚠ Сторінку https://www.minecraft.net/en-us/usage-guidelines під час спайку не вдалося завантажити (тайм-аут). Формулювання дисклеймера у футері («Не є офіційним продуктом Minecraft. Не пов'язано з Mojang або Microsoft», tech.md 10.4) звірити з нею вручну перед релізом (R9).

---

## Мета лоадерів

Фікстури `loaders/` · v1 `packs/clients.py` → `sources/clients/loaders.py` (R1.3)

| Запит | Фікстура | Що читаємо |
| --- | --- | --- |
| `GET https://meta.fabricmc.net/v2/versions/loader/{game}` | `fabric_loader_1.21.1.json` (3 з 255) | `[].loader {version, stable}` |
| `GET https://meta.quiltmc.org/v3/versions/loader/{game}` | `quilt_loader_1.21.1.json` (3 з 310) | `[].loader {version}`; поля `stable` немає, стабільність визначаємо за відсутністю `-beta` / `+` |
| `GET https://files.minecraftforge.net/net/minecraftforge/forge/promotions_slim.json` | `forge_promotions_slim.json` | `promos {"<game>-recommended" \| "<game>-latest": version}` |
| `GET https://maven.neoforged.net/api/maven/versions/releases/net/neoforged/neoforge` | `neoforge_versions.json` | `versions[]` за зростанням; 1.21.1 → `21.1.x`, 26.x → `26.1.0.x` (+ `-alpha…+snapshot-…` для нестабільних) |

- Кеш на стороні джерела 30 хв (`max-age=1800`). Ключі не потрібні.
- Логіка вибору версії лоадера з v1 (`neoforge_prefix`, `_is_stable`) збігається з фікстурами.

---

## Що це змінює в tech.md

1. **Датапаки (R2.1, правило записано).** Спайк 2026-11-09 (`project_datapack.json`, `project_terralith.json` і їхні версії): серед 30 найпопулярніших датапаків для 1.21.1 лише 5 «чистих», решта — моди з окремими файлами `.zip` з лоадером `datapack` (Terralith: файли для `neoforge`, `fabric` і `datapack`). `/project` теж дає `project_type: "mod"`, а `all_project_types` у ньому немає — тип визначаємо за `loaders`: усі лоадери ⊆ {`datapack`, `minecraft`} → `datapack`, інакше `mod`. Мод з лоадером `datapack` показується й у вкладці «Датапаки», а гравцеві без модів (`vanilla`) дістається його `.zip`.
2. **Сервери (R5.2).**
   - Facet-и — у таблиці вище, країну фільтруємо в нас.
   - Мапінг `content`:
     - vanilla → `supported_versions` / `recommended_version`;
     - модпак в окремому проєкті → імпорт `Pack(origin=modrinth)` → `required_pack`;
     - модпак у самому серверному проєкті → теж `required_pack`, але з версії серверного проєкту. Це уточнює 8.2: «власний завантажений пак» доступний через API як версія проєкту, і його теж можна віддати гравцеві як `.mrpack`.
   - Верхньорівневі `game_versions` і `loaders` серверів ігноруємо.
   - `verified_plays_2w` / `verified_plays_4w` бувають `null`, поки Modrinth не порахував гравців (`project_server_no_plays.json`, синхронізація 2026-11-11: 12 з 80 серверів) — вважаємо 0.
3. **MineSkin (R6.2).** Пагінація курсором `after`. Модель і URL текстури — лише з деталей скіна. Без ключа API працює з попередженням `no_api_key`. Спайк 2026-11-11: з 640 рядків галереї назву мають 83, з них 70 технічні (`archmc-…`, частини моделей `…_ARM_LEFT_2`, `….png`); корисних ≈ 5 %. Сторінка скіна — `https://mineskin.org/skins/<uuid>`.
4. **`.mrpack` (R4.3).** Усі файли, які ми додаємо в індекс, беруться з версій Modrinth, тобто з `cdn.modrinth.com`. Дозволений домен для експорту — лише він.
5. **`major` у `/tag/game_version`** записуємо як є в `GameVersion.is_major`, але це не `is_supported`: «підтримувана» = реліз від 1.16 + legacy з налаштувань (6.2).
