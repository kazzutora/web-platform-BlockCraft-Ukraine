"""Short caches for responses that are the same for every guest (catalog pages)."""

import hashlib
from collections.abc import Callable

from django.core.cache import cache
from rest_framework.request import Request
from rest_framework.response import Response

GUEST_TTL = 60


def for_guests(
    request: Request, build: Callable[[], Response], *, ttl: int = GUEST_TTL, vary: str = ""
) -> Response:
    """Guests share the answer for 60 s; signed-in players see their own state, always fresh.

    `vary` separates guests who see different answers for the same URL («Моя гра» cookie).
    """
    if request.user.is_authenticated:
        return build()
    raw = f"{request.get_full_path()}|{vary}"
    key = "guest:" + hashlib.sha256(raw.encode()).hexdigest()
    data = cache.get(key)
    if data is not None:
        return Response(data)
    response = build()
    if response.status_code == 200:
        cache.set(key, response.data, ttl)
    return response


class GuestCachedListMixin:
    """`list()` through `for_guests`; put it before ListModelMixin in the bases."""

    def guest_cache_vary(self, request: Request) -> str:
        return ""

    def list(self, request: Request, *args, **kwargs) -> Response:
        return for_guests(
            request,
            lambda: super(GuestCachedListMixin, self).list(request, *args, **kwargs),
            vary=self.guest_cache_vary(request),
        )
