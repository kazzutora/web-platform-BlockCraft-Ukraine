"""Downloads of v1 were mod files only: their target is the project."""

from django.db import migrations


def fill(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    project_type, _ = ContentType.objects.get_or_create(app_label="mods", model="project")
    Download = apps.get_model("library", "Download")
    for download in Download.objects.filter(content_type__isnull=True).exclude(project=None):
        download.content_type = project_type
        download.object_id = download.project_id
        download.save(update_fields=["content_type", "object_id"])


def unfill(apps, schema_editor):
    # Before 0005 a download was always a mod file: the other kinds cannot go back
    apps.get_model("library", "Download").objects.filter(project=None).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0005_download_any_kind"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [migrations.RunPython(fill, unfill)]
