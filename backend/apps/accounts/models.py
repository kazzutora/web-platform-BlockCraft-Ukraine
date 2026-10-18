from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models.functions import Lower

from apps.core.game import GAME_VERSION_CHOICES, Edition, Loader

from .validators import NICKNAME_MAX_LENGTH, nickname_validators


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **fields) -> "User":
        if not email:
            raise ValueError("Email is required")
        user = self.model(email=self.normalize_email(email).lower(), **fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **fields) -> "User":
        fields.setdefault("is_staff", False)
        fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **fields)

    def create_superuser(self, email: str, password: str | None = None, **fields) -> "User":
        fields.update(is_staff=True, is_superuser=True, role=User.Role.ADMIN)
        return self._create_user(email, password, **fields)


def avatar_upload_to(instance: "User", filename: str) -> str:
    return f"avatars/{instance.pk}/{filename}"


class User(AbstractUser):
    """Signs in with email; the public identity is `nickname`."""

    class Role(models.TextChoices):
        USER = "user", "Гравець"
        TRUSTED = "trusted", "Довірений автор"
        MODERATOR = "moderator", "Модератор"
        ADMIN = "admin", "Адміністратор"

    username = None
    first_name = None
    last_name = None

    email = models.EmailField("email", unique=True)
    nickname = models.CharField(
        "нік", max_length=NICKNAME_MAX_LENGTH, validators=nickname_validators
    )
    avatar = models.ImageField("аватар", upload_to=avatar_upload_to, blank=True)
    bio = models.CharField("про себе", max_length=160, blank=True)
    mc_nickname = models.CharField("нік у Minecraft", max_length=16, blank=True)
    role = models.CharField("роль", max_length=16, choices=Role.choices, default=Role.USER)
    xp = models.PositiveIntegerField(default=0)
    level = models.PositiveSmallIntegerField(default=1)
    is_private = models.BooleanField("закритий профіль", default=False)
    published_count = models.PositiveIntegerField(default=0)

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["nickname"]

    objects = UserManager()

    class Meta:
        verbose_name = "користувач"
        verbose_name_plural = "користувачі"
        constraints = [
            models.UniqueConstraint(Lower("nickname"), name="accounts_user_nickname_ci_unique"),
            models.UniqueConstraint(Lower("email"), name="accounts_user_email_ci_unique"),
        ]

    def __str__(self) -> str:
        return self.nickname

    def get_full_name(self) -> str:
        return self.nickname

    def get_short_name(self) -> str:
        return self.nickname

    @property
    def is_moderator(self) -> bool:
        return self.role in {self.Role.MODERATOR, self.Role.ADMIN} or self.is_superuser


class Interest(models.TextChoices):
    SURVIVAL = "survival", "Виживання"
    BUILDING = "building", "Будівництво"
    TECH = "tech", "Техніка й редстоун"
    PVP = "pvp", "PvP"
    RP = "rp", "Рольова гра"
    ADVENTURE = "adventure", "Пригоди"
    MINIGAMES = "minigames", "Мініігри"
    MODDED = "modded", "Моди й зборки"


class GameProfile(models.Model):
    """How the player plays: drives catalog defaults and «for your version»."""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, primary_key=True, related_name="game_profile"
    )
    game_version = models.CharField(max_length=16, choices=GAME_VERSION_CHOICES, blank=True)
    loader = models.CharField(max_length=16, choices=Loader.choices, blank=True)
    edition = models.CharField(max_length=8, choices=Edition.choices, default=Edition.JAVA)
    interests = ArrayField(
        models.CharField(max_length=16, choices=Interest.choices), default=list, blank=True
    )
    onboarding_done = models.BooleanField(default=False)

    class Meta:
        verbose_name = "ігровий профіль"
        verbose_name_plural = "ігрові профілі"

    def __str__(self) -> str:
        return f"{self.user} · {self.game_version or '—'} · {self.loader or '—'}"


class UserSettings(models.Model):
    class Theme(models.TextChoices):
        LIGHT = "light", "Світла"
        DARK = "dark", "Темна"
        SYSTEM = "system", "Як у системі"

    class Language(models.TextChoices):
        UK = "uk", "Українська"
        EN = "en", "English"

    class CommentPolicy(models.TextChoices):
        ALL = "all", "Усі"
        FOLLOWERS = "followers", "Лише підписники"
        NOBODY = "nobody", "Ніхто"

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, primary_key=True, related_name="settings"
    )
    theme = models.CharField(max_length=8, choices=Theme.choices, default=Theme.LIGHT)
    language = models.CharField(max_length=4, choices=Language.choices, default=Language.UK)
    notify_prefs = models.JSONField(default=dict, blank=True)
    history_enabled = models.BooleanField(default=True)
    who_can_comment = models.CharField(
        max_length=16, choices=CommentPolicy.choices, default=CommentPolicy.ALL
    )
    collections_visible = models.BooleanField(default=True)

    class Meta:
        verbose_name = "налаштування"
        verbose_name_plural = "налаштування"

    def __str__(self) -> str:
        return f"Налаштування {self.user}"
