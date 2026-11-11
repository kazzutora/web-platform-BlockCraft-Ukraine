"""Codes are per player now (`services.claim_code`), not one stored code per server."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("servers", "0007_claims_and_owner_pack")]

    operations = [migrations.RemoveField(model_name="server", name="verify_code")]
