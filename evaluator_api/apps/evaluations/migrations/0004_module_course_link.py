from django.db import migrations, models


def populate_course_link(apps, schema_editor):
    Module = apps.get_model('evaluations', 'Module')
    for module in Module.objects.filter(course_link=''):
        key = module.course_key
        if key.startswith('http'):
            module.course_link = key
            module.save(update_fields=['course_link'])


class Migration(migrations.Migration):

    dependencies = [
        ('evaluations', '0003_seed_rubric'),
    ]

    operations = [
        migrations.AddField(
            model_name='module',
            name='course_link',
            field=models.CharField(blank=True, default='', max_length=500),
        ),
        migrations.RunPython(populate_course_link, migrations.RunPython.noop),
    ]
