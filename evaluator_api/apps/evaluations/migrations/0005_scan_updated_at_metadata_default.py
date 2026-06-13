# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ('evaluations', '0004_module_course_link'),
    ]

    operations = [
        migrations.AddField(
            model_name='scan',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddIndex(
            model_name='scan',
            index=models.Index(
                fields=['updated_at'],
                name='idx_scan_in_progress',
                condition=Q(status='IN_PROGRESS'),
            ),
        ),
        migrations.AlterField(
            model_name='evaluation',
            name='metadata_json',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
