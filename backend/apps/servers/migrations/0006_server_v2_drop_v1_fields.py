from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("servers", "0005_server_v2"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='server',
            name='servers_server_modes_gin',
        ),
        migrations.RemoveIndex(
            model_name='server',
            name='servers_server_status_pub',
        ),
        migrations.RemoveField(
            model_name='server',
            name='author',
        ),
        migrations.RemoveField(
            model_name='server',
            name='banner',
        ),
        migrations.RemoveField(
            model_name='server',
            name='description',
        ),
        migrations.RemoveField(
            model_name='server',
            name='edition',
        ),
        migrations.RemoveField(
            model_name='server',
            name='has_whitelist',
        ),
        migrations.RemoveField(
            model_name='server',
            name='host',
        ),
        migrations.RemoveField(
            model_name='server',
            name='language',
        ),
        migrations.RemoveField(
            model_name='server',
            name='modes',
        ),
        migrations.RemoveField(
            model_name='server',
            name='port',
        ),
        migrations.RemoveField(
            model_name='server',
            name='published_at',
        ),
        migrations.RemoveField(
            model_name='server',
            name='rejection_reason',
        ),
        migrations.RemoveField(
            model_name='server',
            name='status',
        ),
        migrations.RemoveField(
            model_name='server',
            name='versions_label',
        ),
    ]
