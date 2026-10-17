import logging
from typing import Literal, TypedDict

import redis
from django.conf import settings
from django.db import DatabaseError, connection

logger = logging.getLogger(__name__)

CheckStatus = Literal["ok", "error"]


class HealthReport(TypedDict):
    status: CheckStatus
    checks: dict[str, CheckStatus]


def check_database() -> bool:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except DatabaseError:
        logger.warning("Health check: database is unavailable", exc_info=True)
        return False
    return True


def check_redis() -> bool:
    client = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2, socket_timeout=2)
    try:
        return bool(client.ping())
    except redis.RedisError:
        logger.warning("Health check: Redis is unavailable", exc_info=True)
        return False
    finally:
        client.close()


def get_health_report() -> HealthReport:
    results = {"database": check_database(), "redis": check_redis()}
    checks: dict[str, CheckStatus] = {
        name: "ok" if passed else "error" for name, passed in results.items()
    }
    return {"status": "ok" if all(results.values()) else "error", "checks": checks}
