from celery import shared_task

from . import services
from .models import Server


@shared_task(name="servers.ping_all")
def ping_all() -> int:
    """Every 5 minutes: status of all listed servers; returns how many are online."""
    return services.ping_all()


@shared_task(name="servers.ping_server")
def ping_server(server_id: int) -> bool:
    """Right after a server is added or moved: the owner sees it online in seconds."""
    results = services.ping_servers(Server.objects.filter(pk=server_id))
    return bool(results.get(server_id) and results[server_id].is_online)


@shared_task(name="servers.verify_server")
def verify_server(server_id: int) -> str:
    return services.verify(server_id=server_id)
