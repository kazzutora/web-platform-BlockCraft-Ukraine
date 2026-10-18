from celery import shared_task

from . import services


@shared_task(name="skins.render_preview")
def render_preview(skin_id: int) -> bool:
    """On upload or model change: the 2D front view for catalog cards."""
    return services.render_preview(skin_id=skin_id)
