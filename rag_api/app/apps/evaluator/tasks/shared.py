# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging
from pathlib import Path
from typing import Optional
import redis as _redis_lib
import yaml

from django.conf import settings

from rag.pipeline.evaluator import ContentEvaluator
from rag.retrieval import CrossEncoderReranker
from ..bootstrap import build_knowledge_base_auto, load_criteria_auto

logger = logging.getLogger(__name__)

EVAL_CANCELLED_KEY = "eval:cancelled:{}"
CANCEL_FLAG_TTL = 3600

_redis_client = _redis_lib.from_url(settings.CELERY_BROKER_URL)


def get_redis_client():
    """Return the shared Redis client used for the cancel registry."""

    return _redis_client


def is_cancelled(run_id: Optional[str]) -> bool:
    """Return True if a cancel flag is set for this run_id."""

    if not run_id:
        return False
    return bool(_redis_client.exists(EVAL_CANCELLED_KEY.format(run_id)))


def mark_cancelled(run_id: str, ttl: int = CANCEL_FLAG_TTL) -> None:
    """Set the cancel flag for run_id with the given TTL (seconds)."""

    _redis_client.set(EVAL_CANCELLED_KEY.format(run_id), "1", ex=ttl)


def clear_cancel(run_id: Optional[str]) -> None:
    """Remove the cancel flag for run_id, if any."""

    if not run_id:
        return
    _redis_client.delete(EVAL_CANCELLED_KEY.format(run_id))


class EvaluationCancelledError(Exception):
    """Raised inside the evaluation task when a cancel flag is observed."""


# --- Heavy AI singletons (loaded once per process) ---
logger.info("Initializing shared AI models (heavy resources)...")

_config_path = Path(__file__).parents[3] / "config" / "config.yaml"
with open(_config_path, "r", encoding="utf-8") as _f:
    _cfg = yaml.safe_load(_f)
_ce_model = _cfg.get("retrieval", {}).get("cross_encoder_model", "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1")

GLOBAL_VECTOR_STORE, GLOBAL_KB_BM25 = build_knowledge_base_auto()
load_criteria_auto()
GLOBAL_RERANKER = CrossEncoderReranker(model_name=_ce_model)

logger.info("Shared AI models ready.")
