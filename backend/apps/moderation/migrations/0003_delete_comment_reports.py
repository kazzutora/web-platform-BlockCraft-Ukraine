from django.db import migrations


def delete_comment_reports(apps, schema_editor):
    """Reports on comments: comments are removed in v2 (social.0002)."""
    content_type = apps.get_model("contenttypes", "ContentType").objects.filter(
        app_label="social", model="comment"
    )
    apps.get_model("moderation", "Report").objects.filter(content_type__in=content_type).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("moderation", "0002_seed_banned_words"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]
    run_before = [("social", "0002_delete_like_comment")]

    operations = [migrations.RunPython(delete_comment_reports, migrations.RunPython.noop)]
