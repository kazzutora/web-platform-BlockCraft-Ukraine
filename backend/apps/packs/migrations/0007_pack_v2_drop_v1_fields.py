"""Drops v1 pack fields replaced in 0005–0006 (tech.md 6.4: styles and changelog go)."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("packs", "0006_pack_v2_data")]

    operations = [
        migrations.RemoveIndex(model_name="pack", name="packs_pack_styles_gin"),
        migrations.RemoveField(model_name="pack", name="style_tags"),
        migrations.RemoveField(model_name="pack", name="is_official"),
        migrations.RemoveField(model_name="pack", name="install_md"),
        migrations.RemoveField(model_name="pack", name="install_html"),
        migrations.RemoveField(model_name="pack", name="gpu_note"),
        migrations.RemoveField(model_name="pack", name="changelog_md"),
        migrations.RemoveField(model_name="pack", name="changelog_html"),
        migrations.RemoveField(model_name="packitem", name="is_required"),
        migrations.RemoveField(model_name="packitem", name="added_as_dependency"),
        migrations.AlterModelOptions(
            name="pack",
            options={
                "ordering": ["-created_at"],
                "verbose_name": "збірка",
                "verbose_name_plural": "збірки",
            },
        ),
        migrations.AlterModelOptions(
            name="packitem",
            options={
                "ordering": ["position", "pk"],
                "verbose_name": "елемент збірки",
                "verbose_name_plural": "елементи збірки",
            },
        ),
    ]
