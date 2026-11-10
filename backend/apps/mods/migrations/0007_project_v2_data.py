"""Moves v1 data into the v2 fields: Modrinth id, page, visibility, who suggested."""

from django.db import migrations
from django.db.models import CharField, F, Value
from django.db.models.functions import Concat

HIDDEN = ["hidden", "rejected"]


def forward(apps, schema_editor):
    Project = apps.get_model("mods", "Project")
    Project.objects.update(
        external_id=F("modrinth_id"),
        external_url=Concat(
            Value("https://modrinth.com/"),
            F("project_type"),
            Value("/"),
            F("slug"),
            output_field=CharField(),
        ),
        imported_by=F("suggested_by"),
    )
    # Pending suggestions become visible: v2 trusts Modrinth's own moderation (tech.md 6.3)
    Project.objects.filter(status__in=HIDDEN).update(is_hidden=True)


def backward(apps, schema_editor):
    Project = apps.get_model("mods", "Project")
    Project.objects.update(modrinth_id=F("external_id"), suggested_by=F("imported_by"))
    Project.objects.update(status="published")
    Project.objects.filter(is_hidden=True).update(status="hidden")


class Migration(migrations.Migration):
    dependencies = [("mods", "0006_project_v2_fields")]

    operations = [migrations.RunPython(forward, backward)]
