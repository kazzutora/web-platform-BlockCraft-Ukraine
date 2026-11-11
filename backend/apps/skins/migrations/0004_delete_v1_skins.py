"""Skins v1 were uploaded by players; v2 takes skins only from MineSkin and Mojang.

Historical models send no signals, so what pointed at them (saves, reviews, collection
items, reports) is deleted here by content type.
"""

from django.core.files.storage import default_storage
from django.db import migrations

GENERIC = [
    ("library", "Favorite"),
    ("library", "CollectionItem"),
    ("social", "Review"),
    ("moderation", "Report"),
]


def delete_v1_skins(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    skin_type = ContentType.objects.filter(app_label="skins", model="skin").first()
    if skin_type is not None:
        Collection = apps.get_model("library", "Collection")
        CollectionItem = apps.get_model("library", "CollectionItem")
        touched = set(
            CollectionItem.objects.filter(content_type=skin_type).values_list("collection_id", flat=True)
        )
        for app_label, model in GENERIC:
            apps.get_model(app_label, model).objects.filter(content_type=skin_type).delete()
        for collection in Collection.objects.filter(pk__in=touched):
            collection.items_count = CollectionItem.objects.filter(collection=collection).count()
            collection.save(update_fields=["items_count"])
    Skin = apps.get_model("skins", "Skin")
    # The files players uploaded go too: nothing links to them any more
    for skin in Skin.objects.all():
        for name in (skin.file.name, skin.preview.name):
            if name:
                default_storage.delete(name)
    Skin.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("skins", "0003_remove_v1_leftovers"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("library", "0004_remove_v1_leftovers"),
        ("social", "0002_delete_like_comment"),
        ("moderation", "0003_delete_comment_reports"),
    ]

    operations = [migrations.RunPython(delete_v1_skins, migrations.RunPython.noop)]
