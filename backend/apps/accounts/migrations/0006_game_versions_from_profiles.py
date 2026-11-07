from django.db import migrations

from apps.core.versions import is_release


def forwards(apps, schema_editor):
    """Keeps every version players already chose: the first sync fills in the rest of the row."""
    GameProfile = apps.get_model("accounts", "GameProfile")
    GameVersion = apps.get_model("sources", "GameVersion")
    GameProfile.objects.filter(game_version="").update(game_version=None)
    chosen = GameProfile.objects.exclude(game_version=None).values_list("game_version", flat=True)
    for version in set(chosen):
        GameVersion.objects.get_or_create(
            version=version,
            defaults={
                "version_type": "release" if is_release(version) else "snapshot",
                "is_supported": True,
            },
        )


def backwards(apps, schema_editor):
    GameProfile = apps.get_model("accounts", "GameProfile")
    GameProfile.objects.filter(game_version=None).update(game_version="")


class Migration(migrations.Migration):
    """Step 2 of 3: data. The GameVersion rows themselves stay on the way back (sources owns them)."""

    dependencies = [
        ("accounts", "0005_game_version_nullable"),
        ("sources", "0002_gameversion"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
