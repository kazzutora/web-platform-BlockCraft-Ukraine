from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import env

DEBUG = False

SECRET_KEY = env("SECRET_KEY")
if SECRET_KEY.startswith(("change-me", "insecure")):
    raise ImproperlyConfigured("Set a real SECRET_KEY for production.")

# Nginx terminates TLS and forwards the original scheme
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
