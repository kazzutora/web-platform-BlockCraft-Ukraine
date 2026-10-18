from rest_framework.throttling import ScopedRateThrottle

SAFE_METHODS = ("GET", "HEAD", "OPTIONS")


class WriteScopedRateThrottle(ScopedRateThrottle):
    """`throttle_scope` limits only writes; reading stays under the default limits."""

    def allow_request(self, request, view) -> bool:
        if request.method in SAFE_METHODS:
            return True
        return super().allow_request(request, view)
