from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .forms import UserChangeForm, UserCreationForm
from .models import GameProfile, User, UserSettings


class GameProfileInline(admin.StackedInline):
    model = GameProfile
    can_delete = False


class UserSettingsInline(admin.StackedInline):
    model = UserSettings
    can_delete = False


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    ordering = ["-date_joined"]
    list_display = ["nickname", "email", "role", "is_private", "is_active", "date_joined"]
    list_filter = ["role", "is_private", "is_active", "is_staff"]
    search_fields = ["nickname", "email", "mc_nickname"]
    readonly_fields = ["date_joined", "last_login"]
    inlines = [GameProfileInline, UserSettingsInline]
    fieldsets = [
        (None, {"fields": ["email", "password"]}),
        ("Профіль", {"fields": ["nickname", "avatar", "bio", "mc_nickname", "is_private"]}),
        ("Роль і прогрес", {"fields": ["role", "xp", "level", "published_count"]}),
        (
            "Доступ",
            {"fields": ["is_active", "is_staff", "is_superuser", "groups", "user_permissions"]},
        ),
        ("Дати", {"fields": ["last_login", "date_joined"]}),
    ]
    add_fieldsets = [
        (None, {"classes": ["wide"], "fields": ["email", "nickname", "password1", "password2"]}),
    ]
