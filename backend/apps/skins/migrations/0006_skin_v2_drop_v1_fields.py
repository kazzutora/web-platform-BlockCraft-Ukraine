from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("skins", "0005_skin_v2"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='skin',
            name='skins_skin_one_current_per_author',
        ),
        migrations.RemoveIndex(
            model_name='skin',
            name='skins_skin_styles_gin',
        ),
        migrations.RemoveIndex(
            model_name='skin',
            name='skins_skin_status_published',
        ),
        migrations.RemoveField(
            model_name='skin',
            name='author',
        ),
        migrations.RemoveField(
            model_name='skin',
            name='file',
        ),
        migrations.RemoveField(
            model_name='skin',
            name='is_current',
        ),
        migrations.RemoveField(
            model_name='skin',
            name='parent',
        ),
        migrations.RemoveField(
            model_name='skin',
            name='published_at',
        ),
        migrations.RemoveField(
            model_name='skin',
            name='rejection_reason',
        ),
        migrations.RemoveField(
            model_name='skin',
            name='status',
        ),
        migrations.RemoveField(
            model_name='skin',
            name='style_tags',
        ),
    ]
