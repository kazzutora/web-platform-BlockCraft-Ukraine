from celery import shared_task

from . import services


@shared_task(name="social.recalc_scores")
def recalc_scores() -> dict[str, int]:
    """Hourly: Bayesian rating for reviewed kinds, likes for liked kinds."""
    return services.recalc_scores()


@shared_task(name="social.recalc_trends")
def recalc_trends() -> dict[str, int]:
    """Hourly at :45: trend score from the events of the last 14 days."""
    return services.recalc_trends()
