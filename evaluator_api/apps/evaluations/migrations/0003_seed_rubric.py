# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import hashlib
import json
from pathlib import Path

from django.db import migrations

RUBRIC_PATH = Path(__file__).resolve().parent.parent / "rubrics" / "rubric.json"


def seed_rubric(apps, schema_editor):
    Rubric = apps.get_model("evaluations", "Rubric")
    if Rubric.objects.exists():
        return
    content = json.loads(RUBRIC_PATH.read_text(encoding="utf-8"))
    # Self-contained on the historical model: compute content_hash here instead of
    # relying on the live model's save() (which evolves), so this migration keeps
    # working regardless of later model changes.
    normalized = json.dumps(content, sort_keys=True, separators=(",", ":"))
    content_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    Rubric.objects.create(content=content, content_hash=content_hash)


def unseed_rubric(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("evaluations", "0002_initial"),
    ]

    operations = [
        migrations.RunPython(seed_rubric, unseed_rubric),
    ]
