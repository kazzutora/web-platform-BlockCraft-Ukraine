"""Pack v2 (tech.md 6.4): new fields next to the v1 ones; data moves in 0006."""

import django.contrib.postgres.fields
import django.db.models.deletion
from django.db import migrations, models

import apps.packs.models


class Migration(migrations.Migration):
    dependencies = [("packs", "0004_game_version_without_static_choices")]

    operations = [
        migrations.RemoveConstraint(model_name="pack", name="packs_pack_modrinth_id_unique"),
        migrations.RenameField(model_name="pack", old_name="modrinth_id", new_name="external_id"),
        migrations.AlterField(
            model_name="pack",
            name="external_id",
            field=models.CharField(blank=True, max_length=16, verbose_name="id на Modrinth"),
        ),
        migrations.AddConstraint(
            model_name="pack",
            constraint=models.UniqueConstraint(
                condition=models.Q(("external_id", ""), _negated=True),
                fields=("external_id",),
                name="packs_pack_external_id_unique",
            ),
        ),
        migrations.AddField(
            model_name="pack",
            name="origin",
            field=models.CharField(
                choices=[("modrinth", "Modrinth"), ("community", "Спільнота")],
                db_index=True,
                default="community",
                max_length=16,
                verbose_name="звідки",
            ),
        ),
        migrations.AddField(
            model_name="pack",
            name="description_html",
            field=models.TextField(blank=True, editable=False, verbose_name="опис (з Modrinth)"),
        ),
        migrations.AddField(
            model_name="pack",
            name="items_count",
            field=models.PositiveIntegerField(default=0, verbose_name="елементів"),
        ),
        migrations.AddField(
            model_name="pack",
            name="compat_status",
            field=models.CharField(
                choices=[
                    ("ok", "Сумісно"),
                    ("warnings", "Є попередження"),
                    ("errors", "Є проблеми"),
                    ("unknown", "Не перевірено"),
                ],
                default="unknown",
                max_length=8,
                verbose_name="сумісність",
            ),
        ),
        migrations.AddField(
            model_name="pack",
            name="compat_checked_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="перевірено"),
        ),
        migrations.AddField(
            model_name="pack",
            name="compat_report",
            field=models.JSONField(blank=True, default=dict, verbose_name="звіт сумісності"),
        ),
        migrations.AddField(
            model_name="pack",
            name="visibility",
            field=models.CharField(
                choices=[("private", "Лише я"), ("link", "За посиланням"), ("public", "Усім")],
                default="public",
                max_length=8,
                verbose_name="видимість",
            ),
        ),
        migrations.AddField(
            model_name="pack",
            name="share_token",
            field=models.CharField(
                default=apps.packs.models.new_share_token, editable=False, max_length=16
            ),
        ),
        migrations.AddField(
            model_name="pack",
            name="notes_md",
            field=models.TextField(blank=True, max_length=5000, verbose_name="поради автора"),
        ),
        migrations.AddField(
            model_name="pack",
            name="notes_html",
            field=models.TextField(blank=True, editable=False),
        ),
        migrations.AddField(
            model_name="pack",
            name="external_url",
            field=models.URLField(blank=True, max_length=500, verbose_name="сторінка на Modrinth"),
        ),
        migrations.AddField(
            model_name="pack",
            name="synced_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="синхронізовано"),
        ),
        migrations.AddIndex(
            model_name="pack",
            index=models.Index(
                fields=["origin", "game_version", "loader"], name="packs_pack_target"
            ),
        ),
        migrations.AddField(
            model_name="packitem",
            name="reason",
            field=models.CharField(
                choices=[
                    ("requested", "Обрав автор"),
                    ("dependency", "Залежність"),
                    ("implicit", "Потрібен неявно"),
                ],
                default="requested",
                max_length=12,
                verbose_name="чому тут",
            ),
        ),
        migrations.AddField(
            model_name="packitem",
            name="required_by",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=96), blank=True, default=list, size=None
            ),
        ),
        migrations.AddField(
            model_name="packitem",
            name="env_client",
            field=models.CharField(
                choices=[
                    ("required", "Потрібен"),
                    ("optional", "За бажанням"),
                    ("unsupported", "Не потрібен"),
                ],
                default="required",
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name="packitem",
            name="env_server",
            field=models.CharField(
                choices=[
                    ("required", "Потрібен"),
                    ("optional", "За бажанням"),
                    ("unsupported", "Не потрібен"),
                ],
                default="required",
                max_length=12,
            ),
        ),
        migrations.CreateModel(
            name="PackExternalFile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("path", models.CharField(max_length=300)),
                ("url", models.URLField(blank=True, max_length=700)),
                ("sha1", models.CharField(blank=True, max_length=40)),
                ("sha512", models.CharField(blank=True, max_length=128)),
                ("size", models.PositiveBigIntegerField(default=0)),
                (
                    "pack",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="external_files",
                        to="packs.pack",
                    ),
                ),
            ],
            options={
                "verbose_name": "сторонній файл",
                "verbose_name_plural": "сторонні файли",
                "ordering": ["path"],
                "constraints": [
                    models.UniqueConstraint(fields=("pack", "path"), name="packs_external_file_unique")
                ],
            },
        ),
    ]
