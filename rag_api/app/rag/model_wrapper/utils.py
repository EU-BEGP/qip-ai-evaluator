# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import copy
import json
from dataclasses import asdict, dataclass
from typing import Dict, Optional, Type
from pydantic import BaseModel, ValidationError

from .schemas import (
    BatchCriterionEvaluation,
    CriterionEvaluation,
    DocumentSnapshot,
)


MODE_TO_MODEL: dict = {
    "criterion": CriterionEvaluation,
    "batch_criterion": BatchCriterionEvaluation,
    "snapshot": DocumentSnapshot,
}


MODE_TO_TASK: Dict[Optional[str], str] = {
    "criterion": "evaluation",
    "batch_criterion": "evaluation",
    "snapshot": "snapshot",
    None: "metadata",
}


_KEY_ALIASES = {
    "name": "Name",
    "description": "Description",
    "issues": "Issues",
    "results": "evaluations",
}


@dataclass(frozen=True)
class CallConfig:
    """Resolved per-call LLM configuration. Immutable so retry loops can
    derive variants via dataclasses.replace without mutating the original."""

    model: str
    temperature: float = 0.0
    top_p: float = 1.0
    reasoning_effort: Optional[str] = None
    max_completion_tokens: Optional[int] = None


def parse_task_configs(llm_cfg: dict) -> Dict[str, CallConfig]:
    """Build a task, CallConfig dict from the llm_settings block."""

    default_block = llm_cfg.get("default_llm") or llm_cfg.get("processing_llm")
    if not default_block:
        raise ValueError(
            "llm_settings must contain a 'default_llm' (or legacy 'processing_llm') block"
        )

    default_cfg = _build_call_config(default_block)
    configs: Dict[str, CallConfig] = {"default": default_cfg}

    for task_name, override in (llm_cfg.get("task_overrides") or {}).items():
        merged = {**asdict(default_cfg), **(override or {})}
        configs[task_name] = _build_call_config(merged)

    return configs


def _build_call_config(block: dict) -> CallConfig:
    if "model" not in block or not block["model"]:
        raise ValueError("LLM config block missing required 'model' key")
    return CallConfig(
        model=str(block["model"]),
        temperature=float(block.get("temperature", 0.0)),
        top_p=float(block.get("top_p", 1.0)),
        reasoning_effort=block.get("reasoning_effort"),
        max_completion_tokens=block.get("max_completion_tokens"),
    )


def resolve_output_model(mode: Optional[str]) -> Optional[Type[BaseModel]]:
    """Return the structured-output model class for the given mode, or None."""

    if mode is None:
        return None
    return MODE_TO_MODEL.get(mode)


def normalize_keys(obj):
    """Recursively map known lowercase/legacy keys to canonical names."""

    if isinstance(obj, dict):
        return {_KEY_ALIASES.get(k, k): normalize_keys(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [normalize_keys(i) for i in obj]
    return obj


def sanitize_response(text: str) -> str:
    """Pre-Pydantic cleanup for known LLM output drifts.
    - Strip markdown code fences
    - Wrap top-level array as {"evaluations": [...]}
    - Normalize known lowercase/legacy keys
    Returns the original text if JSON parsing fails so downstream surfaces the error.
    """

    text = text.replace("```json", "").replace("```", "").strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return text
    if isinstance(parsed, list):
        parsed = {"evaluations": parsed}
    return json.dumps(normalize_keys(parsed))


def build_feedback_msg(error: ValidationError) -> str:
    """Convert Pydantic validation errors into a corrective message for the LLM."""

    lines = [
        f"- {'.'.join(str(x) for x in err['loc'])}: {err['msg']}"
        for err in error.errors()
    ]
    return (
        "Your previous response did not match the required schema. Specific errors:\n"
        + "\n".join(lines)
        + "\n\nReturn a corrected JSON object matching the schema exactly."
    )


def temp_for_attempt(base_temp: float, attempt: int) -> float:
    """First attempt uses base temperature; later attempts add variance to break loops."""

    bumps = {1: 0.0, 2: 0.3, 3: 0.5}
    return min(1.0, base_temp + bumps.get(attempt, 0.5))


def to_strict_json_schema(model_class: Type[BaseModel]) -> dict:
    """Transform a Pydantic model's JSON schema to be strict-mode compliant
    (OpenAI Structured Outputs)."""

    raw = model_class.model_json_schema()
    return _force_strict(_inline_refs(raw))


def _inline_refs(schema: dict) -> dict:
    """Resolve all $defs/$ref into a fully inlined schema."""

    schema = copy.deepcopy(schema)
    defs = schema.pop("$defs", {})

    def resolve(obj):
        if isinstance(obj, dict):
            if "$ref" in obj:
                ref_name = obj["$ref"].split("/")[-1]
                return resolve(copy.deepcopy(defs.get(ref_name, obj)))
            return {k: resolve(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [resolve(i) for i in obj]
        return obj

    return resolve(schema)


def _force_strict(schema):
    """Recursively enforce OpenAI strict-mode rules: additionalProperties:false,
    all properties in required, no defaults."""

    if isinstance(schema, dict):
        cleaned = {k: _force_strict(v) for k, v in schema.items() if k != "default"}
        if cleaned.get("type") == "object" and "properties" in cleaned:
            cleaned["additionalProperties"] = False
            cleaned["required"] = list(cleaned["properties"].keys())
        return cleaned
    if isinstance(schema, list):
        return [_force_strict(i) for i in schema]
    return schema
