# Діаграма компонентів

```mermaid
flowchart TB
    browser["Браузер<br/>Next.js client components, TanStack Query, skinview3d"]

    subgraph vps["VPS · docker-compose.prod.yml"]
        nginx["Nginx<br/>TLS, CSP, статика й media"]
        next["Next.js 16 (standalone)<br/>Server Components, SSR"]
        django["Django 5.2 + DRF<br/>Gunicorn + Uvicorn"]
        worker["Celery worker"]
        beat["Celery beat<br/>розклад задач"]
        pg[("PostgreSQL 17")]
        redis[("Redis 7<br/>кеш, сесії, черга,<br/>онлайн серверів")]
        meili[("Meilisearch<br/>індекс content")]
        media[("media<br/>скіни, банери, аватари")]
    end

    modrinth["Modrinth API"]
    mojang["Mojang API"]
    mc["Minecraft-сервери<br/>Server List Ping"]
    oauth["Discord, Google OAuth"]
    smtp["SMTP"]

    browser -- "HTTPS, один origin" --> nginx
    nginx -- "/" --> next
    nginx -- "/api, /_allauth, /admin" --> django
    nginx -- "/media, /static" --> media
    next -- "SSR: http://backend:8000 з cookie" --> django
    django --> pg & redis & meili & media
    django -- "кеш 10 / 2 хв" --> mojang
    django --> smtp
    django <-- OAuth --> oauth
    beat -- задачі --> redis
    redis -- задачі --> worker
    worker --> pg & meili & media
    worker -- "щодня 03:00" --> modrinth
    worker -- "кожні 5 хв, ≤ 20 паралельно" --> mc
```

## Застосунки бекенду

| Застосунок | Відповідає за | Зовнішнє |
| --- | --- | --- |
| `core` | Kinds-реєстр, міксини моделей, лічильники, публікація, помилки API, транслітерація, кеш для гостей | — |
| `accounts` | Користувач, профіль гри, налаштування, експорт і видалення даних | allauth (email, Discord, Google) |
| `mods` | Каталог Modrinth, версії, підбір файлу, переклади описів | Modrinth (Celery) |
| `skins` | Перевірка PNG, модель slim/classic, колір, 2D-прев'ю, пошук за ніком | Mojang (з кешем) |
| `servers` | Сервери, пінг, статус у Redis, статистика, верифікація MOTD, SSRF-захист | Minecraft-сервери (Celery) |
| `library` | Обране, колекції, редактори, посилання з токеном, завантаження | — |
| `social` | Лайки, відгуки, коментарі, рейтинг і тренди | — |
| `search` | Документи, індексація через сигнали, пошук із запасним варіантом у БД | Meilisearch |
| `home` | Головна, топи, демо-дані (`make seed`) | — |
| `moderation` | Скарги, автоприховування, санкції, фільтр лексики | — |
| `notifications` | Сповіщення й лічильник непрочитаних | — |

## Шари всередині застосунку

`models` (лише поля) → `services` (усі зміни стану, транзакції) → `selectors` (складне читання, анотації без N+1) → `serializers` → `views` (тонкі) → `urls`. Зовнішні API — у `clients.py`, фонові задачі — у `tasks.py`.
