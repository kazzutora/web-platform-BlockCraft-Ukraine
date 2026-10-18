from celery import shared_task

from . import services


@shared_task(name="moderation.lift_expired_bans")
def lift_expired_bans() -> int:
    """Hourly: players whose ban ran out can sign in again."""
    return services.lift_expired_bans()
