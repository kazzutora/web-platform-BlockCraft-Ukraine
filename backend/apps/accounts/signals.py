from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.core.game import GAME_COOKIE

from . import services
from .models import User


@receiver(post_save, sender=User, dispatch_uid="accounts_create_profiles")
def create_profiles(sender: type[User], instance: User, created: bool, **kwargs) -> None:
    # Covers every way to create a user: sign-up, social login, admin, createsuperuser
    if created:
        services.ensure_profiles(user=instance)


@receiver(user_logged_in, dispatch_uid="accounts_adopt_guest_game")
def adopt_guest_game(sender, request, user: User, **kwargs) -> None:
    if request is not None:
        services.adopt_guest_game(user=user, cookie=request.COOKIES.get(GAME_COOKIE))
