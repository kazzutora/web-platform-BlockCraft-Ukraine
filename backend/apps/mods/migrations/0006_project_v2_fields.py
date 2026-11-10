"""Project v2 (tech.md 6.3): source fields next to the v1 ones; data moves in 0007."""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mods", "0005_remove_v1_leftovers"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameField(
            model_name="projectversion", old_name="released_at", new_name="date_published"
        ),
        migrations.AddField(
            model_name="project",
            name="source",
            field=models.CharField(
                choices=[
                    ("modrinth", "Modrinth"),
                    ("mineskin", "MineSkin"),
                    ("mojang", "Mojang"),
                    ("owner", "Власник"),
                ],
                db_index=True,
                default="modrinth",
                max_length=16,
                verbose_name="джерело",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="project",
            name="external_id",
            field=models.CharField(default="", max_length=64, verbose_name="id у джерелі"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="project",
            name="external_url",
            field=models.URLField(blank=True, max_length=500, verbose_name="сторінка в джерелі"),
        ),
        migrations.AddField(
            model_name="project",
            name="is_hidden",
            field=models.BooleanField(db_index=True, default=False, verbose_name="приховано в нас"),
        ),
        migrations.AddField(
            model_name="project",
            name="hidden_reason",
            field=models.CharField(blank=True, max_length=280, verbose_name="чому приховано"),
        ),
        migrations.AddField(
            model_name="project",
            name="client_side",
            field=models.CharField(
                choices=[
                    ("required", "Потрібен"),
                    ("optional", "Необов’язковий"),
                    ("unsupported", "Не працює"),
                    ("unknown", "Невідомо"),
                ],
                default="unknown",
                max_length=12,
                verbose_name="на клієнті",
            ),
        ),
        migrations.AddField(
            model_name="project",
            name="server_side",
            field=models.CharField(
                choices=[
                    ("required", "Потрібен"),
                    ("optional", "Необов’язковий"),
                    ("unsupported", "Не працює"),
                    ("unknown", "Невідомо"),
                ],
                default="unknown",
                max_length=12,
                verbose_name="на сервері",
            ),
        ),
        migrations.AddField(
            model_name="project",
            name="modrinth_follows",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="project",
            name="versions_synced_at",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="версії синхронізовано"
            ),
        ),
        migrations.AddField(
            model_name="project",
            name="imported_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="imported_projects",
                to=settings.AUTH_USER_MODEL,
                verbose_name="додав за посиланням",
            ),
        ),
    ]
