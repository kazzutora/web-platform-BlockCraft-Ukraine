import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Step 3 of 3: the profile points at sources.GameVersion."""

    dependencies = [
        ("accounts", "0006_game_versions_from_profiles"),
        ("sources", "0002_gameversion"),
    ]

    operations = [
        migrations.AlterField(
            model_name="gameprofile",
            name="game_version",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="sources.gameversion",
                verbose_name="версія гри",
            ),
        ),
    ]
