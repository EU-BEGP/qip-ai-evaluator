# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import json
from pathlib import Path

from django.db import migrations

RUBRIC_PATH = Path(__file__).resolve().parent.parent / "rubrics" / "rubric.json"


def seed_rubric(apps, schema_editor):
    Rubric = apps.get_model("evaluations", "Rubric")
    if Rubric.objects.exists():
        return
    content = json.loads(RUBRIC_PATH.read_text(encoding="utf-8"))
    # Use the real model (not historical) so save() computes content_hash and rubric_map.
    from apps.evaluations.models import Rubric as RealRubric
    RealRubric.objects.create(content=content)


def unseed_rubric(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("evaluations", "0002_initial"),
    ]

    operations = [
        migrations.RunPython(seed_rubric, unseed_rubric),
    ]
