from django.db.models.signals import post_save
from django.dispatch import receiver

from . import services
from .models import User


@receiver(post_save, sender=User, dispatch_uid="accounts_create_profiles")
def create_profiles(sender: type[User], instance: User, created: bool, **kwargs) -> None:
    # Covers every way to create a user: sign-up, social login, admin, createsuperuser
    if created:
        services.ensure_profiles(user=instance)
