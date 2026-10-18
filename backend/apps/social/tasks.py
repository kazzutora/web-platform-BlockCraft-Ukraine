from celery import shared_task

from . import services


@shared_task(name="social.recalc_scores")
def recalc_scores() -> dict[str, int]:
    """Hourly: Bayesian rating for reviewed kinds, likes for liked kinds."""
    return services.recalc_scores()
