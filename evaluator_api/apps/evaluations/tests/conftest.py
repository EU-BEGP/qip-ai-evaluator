# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import json
from pathlib import Path

from django.contrib.auth import get_user_model

from apps.evaluations.models import Rubric
from apps.evaluations.services.life_cycle_service import LifecycleService

User = get_user_model()
COURSE_KEY = "https://time.learnify.se/l/show.html#att/68K7V"

_RUBRIC_PATH = Path(__file__).resolve().parent.parent / "rubrics" / "rubric.json"


def ensure_rubric():
    """Return the active rubric, creating it from rubric.json if the DB is empty.

    The seed migration uses the real model so save() computes content_hash and
    rubric_map, but in isolated test transactions the migration data may not be
    present — this function guarantees a usable rubric regardless."""

    rubric = Rubric.objects.first()
    if rubric is None:
        content = json.loads(_RUBRIC_PATH.read_text(encoding="utf-8"))
        rubric = Rubric.objects.create(content=content)
    return rubric


def make_user(email="user@test.com", password="pass"):
    return User.objects.create_user(email=email, password=password)


def make_evaluation(user, course_key=COURSE_KEY):
    module = LifecycleService.ensure_module_access(user, course_key)
    evaluation, _ = LifecycleService.get_or_create_evaluation_structure(module, user)
    return module, evaluation
