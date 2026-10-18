"""Short caches for responses that are the same for every guest (catalog pages)."""

import hashlib
from collections.abc import Callable

from django.core.cache import cache
from rest_framework.request import Request
from rest_framework.response import Response

GUEST_TTL = 60


def for_guests(
    request: Request, build: Callable[[], Response], *, ttl: int = GUEST_TTL
) -> Response:
    """Guests share the answer for 60 s; signed-in players see their own state, always fresh."""
    if request.user.is_authenticated:
        return build()
    key = "guest:" + hashlib.sha256(request.get_full_path().encode()).hexdigest()
    data = cache.get(key)
    if data is not None:
        return Response(data)
    response = build()
    if response.status_code == 200:
        cache.set(key, response.data, ttl)
    return response


class GuestCachedListMixin:
    """`list()` through `for_guests`; put it before ListModelMixin in the bases."""

    def list(self, request: Request, *args, **kwargs) -> Response:
        return for_guests(
            request, lambda: super(GuestCachedListMixin, self).list(request, *args, **kwargs)
        )
