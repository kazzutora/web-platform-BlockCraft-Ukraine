# Деплой на VPS

Один сервер, Docker Compose, HTTPS від Let's Encrypt. Усе описане нижче — для Ubuntu 24.04, але підійде будь-який Linux із Docker.

## Що потрібно

- VPS: 2 vCPU, 4 ГБ RAM, 30 ГБ диска (PostgreSQL, Meilisearch і два образи збираються на сервері).
- Домен, наприклад `blockcraft.ua`: записи `A` для `blockcraft.ua` і `www.blockcraft.ua` на IP сервера.
- Docker Engine 27+ з плагіном Compose, `git`.
- Поштова скринька для листів сайту (SMTP): підтвердження email і скидання пароля.

## Перший запуск

```sh
sudo mkdir -p /srv/blockcraft && sudo chown "$USER" /srv/blockcraft
git clone https://github.com/kazzutora/web-platform-BlockCraft-Ukraine.git /srv/blockcraft
cd /srv/blockcraft
cp .env.example .env
```

У `.env` заповнити (решта — як у прикладі):

| Змінна | Значення |
| --- | --- |
| `ENV`, `DEBUG` | `prod`, `0` |
| `SECRET_KEY` | `python3 -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DOMAIN`, `CERTBOT_EMAIL` | домен без `https://` і пошта для листів Let's Encrypt |
| `SITE_URL`, `NEXT_PUBLIC_SITE_URL` | `https://DOMAIN` |
| `ALLOWED_HOSTS` | `DOMAIN,localhost,backend` (`localhost` — для healthcheck, `backend` — для SSR) |
| `CSRF_TRUSTED_ORIGINS` | `https://DOMAIN` |
| `POSTGRES_PASSWORD`, `DATABASE_URL` | новий пароль в обох |
| `MEILI_MASTER_KEY` | випадковий рядок від 16 символів |
| `EMAIL_BACKEND` | `django.core.mail.backends.smtp.EmailBackend` |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` | дані SMTP |
| `DISCORD_*`, `GOOGLE_*` | ключі OAuth (callback: `https://DOMAIN/accounts/<provider>/login/callback/`) |
| `MODRINTH_USER_AGENT` | `blockcraft-ua/1.0 (contact: ваша-пошта)` |

Збірка, сертифікат і старт:

```sh
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml run --rm static        # статичні файли адмінки
sh infra/scripts/init-letsencrypt.sh                             # перший сертифікат
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
docker compose -f docker-compose.prod.yml exec backend python manage.py sync_mods
docker compose -f docker-compose.prod.yml exec backend python manage.py reindex_search
```

Міграції запускаються самі при кожному старті `backend`. Сертифікат оновлює сервіс `certbot` (двічі на добу), Nginx перечитує його кожні 6 годин.

Перевірка: `https://DOMAIN/api/v1/health` → `{"status": "ok", …}`, `docker compose -f docker-compose.prod.yml ps` — усі сервіси `healthy` або `running`.

## Оновлення: тег → GitHub Actions

`.github/workflows/deploy.yml` на тег `v*` проганяє весь CI і по SSH оновлює сервер (`git checkout <тег>`, збірка, перезапуск), потім перевіряє `/api/v1/health`.

Один раз налаштувати:

1. На сервері — окремий ключ для деплою: `ssh-keygen -t ed25519 -f ~/.ssh/deploy -N ""`, публічну частину додати в `~/.ssh/authorized_keys`.
2. У GitHub → Settings → Environments створити `production`, у Secrets репозиторію додати `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_PATH` (`/srv/blockcraft`), `DEPLOY_SSH_KEY` (вміст `~/.ssh/deploy`) і `DEPLOY_KNOWN_HOSTS` (вивід `ssh-keyscan -t ed25519 <host>`, звірений з відбитком сервера); у Variables — `SITE_URL`.

Реліз:

```sh
git tag v0.9.0 && git push origin v0.9.0
```

## Резервні копії

`infra/scripts/backup.sh` робить дамп БД (`pg_dump -Fc`) і архів `media` у `backups/`, тримає 7 днів (`BACKUP_KEEP_DAYS`). Cron на сервері:

```cron
15 4 * * * cd /srv/blockcraft && sh infra/scripts/backup.sh >> backups/backup.log 2>&1
```

Копію `backups/` варто регулярно забирати з сервера (наприклад, `rsync` на інший комп'ютер або в хмару).

Відновлення на чистому сервері (після «Першого запуску» без `sync_mods`):

```sh
sh infra/scripts/restore.sh backups/db_2026-10-18_0415.dump backups/media_2026-10-18_0415.tar.gz
```

Скрипт замінює вміст БД, розпаковує файли, перезапускає стек і перебудовує пошуковий індекс. Перевірено: дамп dev-бази (500 проєктів, 87 тис. версій) відновлюється в порожній PostgreSQL 17 з тими самими кількостями рядків.

## Корисне

```sh
docker compose -f docker-compose.prod.yml logs -f backend worker   # логи
docker compose -f docker-compose.prod.yml exec backend python manage.py shell
docker compose -f docker-compose.prod.yml exec db psql -U blockcraft
```
