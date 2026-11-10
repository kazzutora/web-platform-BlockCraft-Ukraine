"""Projects from v1 have Modrinth's `updated` but none of the new fields (client_side…).

Forgetting the date makes the next catalog sync read every page again instead of counting
them as unchanged (R2 review).
"""

from django.db import migrations


def forward(apps, schema_editor):
    apps.get_model("mods", "Project").objects.filter(client_side="unknown").update(
        modrinth_updated_at=None
    )


class Migration(migrations.Migration):
    dependencies = [("mods", "0008_project_v2_drop_v1_fields")]

    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
