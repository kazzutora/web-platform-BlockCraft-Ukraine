"""Moves v1 pack data into the v2 fields (tech.md 6.4).

- `is_official` → `origin=modrinth` with a link to the modpack page;
- `install_md` + `gpu_note` → `notes_md` (R0.3 decision), rendered again;
- every pack gets its own share token (AddField gave all rows the same one);
- items: `added_as_dependency` → `reason`, `is_required=False` → optional on both sides.
"""

import secrets

from django.db import migrations
from django.db.models import Count, F, OuterRef, Subquery, Value
from django.db.models.functions import Concat


def forward(apps, schema_editor):
    from apps.mods.markdown import render_markdown

    Pack = apps.get_model("packs", "Pack")
    PackItem = apps.get_model("packs", "PackItem")

    Pack.objects.filter(is_official=True).update(
        origin="modrinth",
        external_url=Concat(Value("https://modrinth.com/modpack/"), F("external_id")),
    )
    for pack in Pack.objects.all().only("pk", "install_md", "gpu_note"):
        notes = "\n\n".join(
            part for part in (pack.install_md.strip(), pack.gpu_note.strip()) if part
        )
        Pack.objects.filter(pk=pack.pk).update(
            notes_md=notes[:5000],
            notes_html=render_markdown(notes[:5000]),
            share_token=secrets.token_urlsafe(12)[:16],
        )
    counts = (
        PackItem.objects.filter(pack=OuterRef("pk"))
        .order_by()
        .values("pack")
        .annotate(n=Count("pk"))
        .values("n")
    )
    Pack.objects.update(items_count=Subquery(counts))
    Pack.objects.filter(items_count__isnull=True).update(items_count=0)
    PackItem.objects.filter(added_as_dependency=True).update(reason="dependency")
    PackItem.objects.filter(is_required=False).update(env_client="optional", env_server="optional")


def backward(apps, schema_editor):
    Pack = apps.get_model("packs", "Pack")
    PackItem = apps.get_model("packs", "PackItem")
    Pack.objects.filter(origin="modrinth").update(is_official=True)
    Pack.objects.update(install_md=F("notes_md"), install_html=F("notes_html"))
    PackItem.objects.exclude(reason="requested").update(added_as_dependency=True)
    PackItem.objects.filter(env_client="optional").update(is_required=False)


class Migration(migrations.Migration):
    dependencies = [("packs", "0005_pack_v2_fields"), ("mods", "0009_reread_v1_projects")]

    operations = [migrations.RunPython(forward, backward)]
