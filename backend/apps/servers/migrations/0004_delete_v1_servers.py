"""Servers v1 were added by hand without a source; v2 mirrors Modrinth and proven owners.

Historical models send no signals, so what pointed at them (saves, reviews, collection
items, reports) is deleted here by content type.
"""

from django.db import migrations

GENERIC = [
    ("library", "Favorite"),
    ("library", "CollectionItem"),
    ("social", "Review"),
    ("moderation", "Report"),
]


def delete_v1_servers(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    server_type = ContentType.objects.filter(app_label="servers", model="server").first()
    if server_type is not None:
        Collection = apps.get_model("library", "Collection")
        CollectionItem = apps.get_model("library", "CollectionItem")
        touched = set(
            CollectionItem.objects.filter(content_type=server_type).values_list("collection_id", flat=True)
        )
        for app_label, model in GENERIC:
            apps.get_model(app_label, model).objects.filter(content_type=server_type).delete()
        for collection in Collection.objects.filter(pk__in=touched):
            collection.items_count = CollectionItem.objects.filter(collection=collection).count()
            collection.save(update_fields=["items_count"])
    apps.get_model("servers", "Server").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("servers", "0003_remove_v1_leftovers"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("library", "0004_remove_v1_leftovers"),
        ("social", "0002_delete_like_comment"),
        ("moderation", "0003_delete_comment_reports"),
    ]

    operations = [migrations.RunPython(delete_v1_servers, migrations.RunPython.noop)]
