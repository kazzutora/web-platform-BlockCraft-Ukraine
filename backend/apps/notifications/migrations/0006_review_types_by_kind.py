"""«review» becomes «review_on_your_pack» / «review_on_your_server» by the reviewed kind;
the rest of v1 review notifications (skins, collections) have nobody to tell any more."""

from django.db import migrations

BY_KIND = {"pack": "review_on_your_pack", "server": "review_on_your_server"}


def retype(apps, schema_editor):
    Notification = apps.get_model("notifications", "Notification")
    # A player who switched «review» off keeps both new types off
    UserSettings = apps.get_model("accounts", "UserSettings")
    for settings in UserSettings.objects.filter(notify_prefs__has_key="review"):
        prefs = dict(settings.notify_prefs)
        enabled = prefs.pop("review")
        for new in BY_KIND.values():
            prefs.setdefault(new, enabled)
        settings.notify_prefs = prefs
        settings.save(update_fields=["notify_prefs"])
    for note in Notification.objects.filter(type="review"):
        new = BY_KIND.get((note.payload or {}).get("kind"))
        if new is None:
            note.delete()
        else:
            note.type = new
            note.save(update_fields=["type"])


class Migration(migrations.Migration):
    dependencies = [("notifications", "0005_v2_types"), ("accounts", "0008_usersettings_skin")]

    operations = [migrations.RunPython(retype, migrations.RunPython.noop)]
