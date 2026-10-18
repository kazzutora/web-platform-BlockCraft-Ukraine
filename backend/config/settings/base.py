from pathlib import Path

import environ
from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()

SECRET_KEY = env("SECRET_KEY", default="insecure-dev-key")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
SITE_URL = env("SITE_URL", default="http://localhost:8080")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.postgres",
    "rest_framework",
    "django_filters",
    "drf_spectacular",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.discord",
    "allauth.socialaccount.providers.google",
    "allauth.headless",
    "apps.core",
    "apps.accounts",
    "apps.library",
    "apps.social",
    "apps.mods",
    "apps.skins",
    "apps.servers",
    "apps.search",
    "apps.home",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "config.urls"

# Site name and domain are used in emails (core migration 0001 fills them from SITE_URL)
SITE_ID = 1
SITE_NAME = "BlockCraft Ukraine"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Database and cache

DATABASES = {"default": env.db("DATABASE_URL")}

REDIS_URL = env("REDIS_URL")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"

# Auth: email + password and Discord / Google through allauth headless (browser client).
# The SPA talks to /_allauth/browser/v1/…; Django keeps the session cookie on our origin.

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

ACCOUNT_ADAPTER = "apps.accounts.adapters.AccountAdapter"
ACCOUNT_USER_MODEL_USERNAME_FIELD = "nickname"
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "username*", "password1*"]
ACCOUNT_USERNAME_MIN_LENGTH = 3
ACCOUNT_USERNAME_VALIDATORS = "apps.accounts.validators.nickname_validators"
ACCOUNT_PRESERVE_USERNAME_CASING = True
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_LOGOUT_ON_PASSWORD_CHANGE = False
ACCOUNT_EMAIL_SUBJECT_PREFIX = "BlockCraft · "

HEADLESS_ONLY = True
HEADLESS_CLIENTS = ("browser",)
HEADLESS_SERVE_SPECIFICATION = True
HEADLESS_FRONTEND_URLS = {
    "account_confirm_email": f"{SITE_URL}/verify-email/{{key}}",
    "account_reset_password": f"{SITE_URL}/password-reset",
    "account_reset_password_from_key": f"{SITE_URL}/password-reset/{{key}}",
    "account_signup": f"{SITE_URL}/register",
    "socialaccount_login_error": f"{SITE_URL}/login?error=social",
}


def _oauth_apps(client_id: str, secret: str) -> list[dict[str, str]]:
    # A provider shows up on the sign-in page only when its keys are configured
    return [{"client_id": client_id, "secret": secret, "key": ""}] if client_id else []


SOCIALACCOUNT_PROVIDERS = {
    "discord": {
        "APPS": _oauth_apps(
            env("DISCORD_CLIENT_ID", default=""), env("DISCORD_CLIENT_SECRET", default="")
        ),
        "SCOPE": ["identify", "email"],
    },
    "google": {
        "APPS": _oauth_apps(
            env("GOOGLE_CLIENT_ID", default=""), env("GOOGLE_CLIENT_SECRET", default="")
        ),
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
    },
}
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_STORE_TOKENS = False

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization

LANGUAGE_CODE = "uk"
TIME_ZONE = "Europe/Kyiv"
USE_I18N = True
USE_TZ = True

# Static and media files

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Email

EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="BlockCraft <no-reply@example.com>")

# Django REST framework

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.core.exceptions.handler",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "120/min",
        "uploads": "20/hour",
        "comments": "30/hour",
        "reviews": "20/day",
        "reports": "20/day",
        "lookup": "30/min",
        "copy_ip": "60/hour",
    },
    # Nginx (and Next.js for SSR) set X-Forwarded-For; throttles count the real client
    "NUM_PROXIES": 1,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "BlockCraft API",
    "DESCRIPTION": "API of the BlockCraft Ukraine community platform.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": r"/api/v1",
    "ENUM_NAME_OVERRIDES": {
        "CheckStatusEnum": ["ok", "error"],
        # Same field names with different choices in several apps
        "EditionEnum": "apps.core.game.Edition",
        "ServerEditionEnum": "apps.servers.choices.Edition",
        "LanguageEnum": "apps.accounts.models.UserSettings.Language",
        "ServerLanguageEnum": "apps.servers.choices.Language",
        "PublishStatusEnum": "apps.core.models.Publishable.Status",
    },
}

# Celery

CELERY_BROKER_URL = REDIS_URL
CELERY_TASK_IGNORE_RESULT = True
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TIME_LIMIT = 5 * 60
CELERY_TASK_SOFT_TIME_LIMIT = 4 * 60
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BEAT_SCHEDULE: dict[str, dict] = {
    "mods-sync-popular": {"task": "mods.sync_popular", "schedule": crontab(hour=3, minute=0)},
    "mods-sync-versions-for-tracked": {
        "task": "mods.sync_versions_for_tracked",
        "schedule": crontab(hour=3, minute=30),
    },
    "social-recalc-scores": {"task": "social.recalc_scores", "schedule": crontab(minute=15)},
    "servers-ping-all": {"task": "servers.ping_all", "schedule": crontab(minute="*/5")},
    "social-recalc-trends": {"task": "social.recalc_trends", "schedule": crontab(minute=45)},
    "search-reindex-all": {"task": "search.reindex_all", "schedule": crontab(hour=5, minute=0)},
}

# Search (Meilisearch)

MEILI_URL = env("MEILI_URL", default="http://meili:7700")
MEILI_MASTER_KEY = env("MEILI_MASTER_KEY", default="")
SEARCH_INDEX = env("SEARCH_INDEX", default="content")
# Signals queue index updates; tests switch it off and mock the search engine
SEARCH_INDEXING = env.bool("SEARCH_INDEXING", default=True)

# Modrinth

MODRINTH_USER_AGENT = env(
    "MODRINTH_USER_AGENT", default="blockcraft-ua/1.0 (contact: you@example.com)"
)
# Projects and versions are synced for the releases listed in apps/core/game.py
MODRINTH_SYNC_LIMITS = {
    "mod": env.int("MODRINTH_SYNC_LIMIT_MODS", default=300),
    "resourcepack": env.int("MODRINTH_SYNC_LIMIT_RESOURCEPACKS", default=100),
    "shader": env.int("MODRINTH_SYNC_LIMIT_SHADERS", default=100),
}
