from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from . import words
from .models import BannedWord


@receiver([post_save, post_delete], sender=BannedWord, dispatch_uid="moderation.words.cache")
def _forget_words(**kwargs) -> None:
    words.forget_cache()
