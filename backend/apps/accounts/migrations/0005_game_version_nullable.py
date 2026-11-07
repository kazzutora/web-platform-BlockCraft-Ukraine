from django.db import migrations, models


class Migration(migrations.Migration):
    """Step 1 of 3: the static choices go; NULL becomes «not chosen» instead of ""."""

    dependencies = [
        ("accounts", "0004_remove_v1_progress_and_interests"),
    ]

    operations = [
        migrations.AlterField(
            model_name="gameprofile",
            name="game_version",
            field=models.CharField(blank=True, max_length=16, null=True),
        ),
    ]
