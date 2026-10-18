from .base import *  # noqa: F403
from .base import CELERY_BEAT_SCHEDULE, env

DEBUG = env.bool("DEBUG", default=True)

CELERY_BEAT_SCHEDULE = {
    **CELERY_BEAT_SCHEDULE,
    # Heartbeat that shows the worker and beat are alive in `make logs`
    "core-ping": {"task": "core.ping", "schedule": 5 * 60},
}
