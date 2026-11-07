from django.db import migrations


def trusted_to_user(apps, schema_editor):
    """The «trusted author» role went away with the «first three works» moderation queue."""
    apps.get_model("accounts", "User").objects.filter(role="trusted").update(role="user")


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_remove_who_can_comment")]

    # Who was trusted is not recorded anywhere else: the reverse keeps everyone a player
    operations = [migrations.RunPython(trusted_to_user, migrations.RunPython.noop)]
