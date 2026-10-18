from urllib.parse import urlparse

from django.conf import settings
from django.db import migrations


def set_site(apps, schema_editor):
    Site = apps.get_model("sites", "Site")
    domain = urlparse(settings.SITE_URL).netloc or "localhost"
    Site.objects.update_or_create(
        id=settings.SITE_ID, defaults={"domain": domain, "name": settings.SITE_NAME}
    )


def reset_site(apps, schema_editor):
    Site = apps.get_model("sites", "Site")
    Site.objects.filter(id=settings.SITE_ID).update(domain="example.com", name="example.com")


class Migration(migrations.Migration):
    dependencies = [("sites", "0002_alter_domain_unique")]

    operations = [migrations.RunPython(set_site, reset_site)]
