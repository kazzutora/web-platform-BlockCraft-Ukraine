from django.contrib.auth.models import AnonymousUser
from django.http import Http404

from .models import User


def get_profile_user(*, nickname: str) -> User:
    """Active user by nickname, ignoring case."""
    try:
        return User.objects.select_related("game_profile").get(
            nickname__iexact=nickname, is_active=True
        )
    except User.DoesNotExist as error:
        raise Http404 from error


def can_view_full_profile(*, viewer: User | AnonymousUser, owner: User) -> bool:
    """Closed profiles show only the nickname to everyone except the owner and moderators."""
    if not owner.is_private:
        return True
    if not viewer.is_authenticated:
        return False
    return viewer.pk == owner.pk or viewer.is_moderator
