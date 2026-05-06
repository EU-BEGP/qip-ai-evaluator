# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import json
import logging
import os
import random
import threading
from typing import Dict, List, Optional, Union

from groq import Groq
from pydantic import BaseModel, Field, model_validator, ValidationError

from ..base import BaseLLMWrapper

logger = logging.getLogger(__name__)
_shared_keys: List[str] = []
_shared_clients: Dict[str, Groq] = {}
_shared_index: int = 0
_shared_lock = threading.Lock()


def _register_keys(keys: List[str]) -> None:
    """Initialize the module-level key pool on first call; no-op afterwards."""

    global _shared_keys, _shared_clients, _shared_index
    with _shared_lock:
        if _shared_keys:
            return
        shuffled = keys[:]
        random.shuffle(shuffled)
        _shared_keys = shuffled
        _shared_clients = {k: Groq(api_key=k) for k in shuffled}
        _shared_index = 0
        logger.info(f"Groq key pool initialized with {len(_shared_keys)} key(s).")


def _next_key_rotation() -> List[str]:
    """Return all keys in round-robin order starting from the next position."""

    global _shared_index
    with _shared_lock:
        idx = _shared_index % len(_shared_keys)
        _shared_index += 1
    return _shared_keys[idx:] + _shared_keys[:idx]


class CriterionEvaluation(BaseModel):
    """Structured output for a single criterion evaluation."""

    Name: str
    Shortcomings: List[str] = Field(..., description="List of shortcomings found")
    Recommendations: List[str] = Field(..., description="List of recommendations, one per shortcoming")
    Deductions: List[float] = Field(..., description="Numeric deductions matching each shortcoming")
    Description: str = Field(..., description="Summary of the overall analysis")

    @model_validator(mode="after")
    def check_validity(self) -> "CriterionEvaluation":
        s, r, d = self.Shortcomings, self.Recommendations, self.Deductions
        if not (len(s) == len(r) == len(d)):
            raise ValueError(
                f"List length mismatch: Shortcomings={len(s)}, "
                f"Recommendations={len(r)}, Deductions={len(d)}. All must match."
            )
        if not self.Description or not self.Description.strip():
            raise ValueError("Description cannot be empty.")
        if not s and not r and not d:
            self.Shortcomings = ["NO SHORTCOMINGS"]
            self.Recommendations = ["NO RECOMMENDATIONS"]
            self.Deductions = [0.0]
        return self


class DocumentSnapshot(BaseModel):
    """Structured digest extracted verbatim from a module document."""

    Title: str = Field(..., description="Module title")
    Keywords: List[str] = Field(..., description="Keywords as a list of strings")
    Abstract: str = Field(..., description="Abstract section")
    IntendedLearningOutcomesKnowledge: str = Field(..., description="Learning outcomes: Knowledge")
    IntendedLearningOutcomesSkills: str = Field(..., description="Learning outcomes: Skills")
    IntendedLearningOutcomesResponsibility: str = Field(..., description="Learning outcomes: Responsibility")
    Outline: List[str] = Field(..., description="Ordered list of major sections/headings")
    ImportantInformation: List[str] = Field(
        ..., description="Verbatim sentences copied directly from the document — no paraphrasing"
    )


class ModuleMetadata(BaseModel):
    """Combined output from basic metadata + EQF level extraction prompts."""

    title: str = Field(..., description="The official title of the module")
    abstract: str = Field(..., description="Summary of the module content")
    uniqueness: str = Field(..., description="Explanation of what makes this module unique")
    societal_relevance: str = Field(..., description="How this module impacts society")
    elh: str = Field(..., description="Estimated Learning Hours (ELH) value")
    eqf: str = Field(..., description="European Qualification Framework (EQF) level")
    smcts: str = Field(..., description="SMCTS credit value")
    teachers: str = Field(..., description="Names and details of teachers/authors")
    keywords: List[str] = Field(..., description="List of keywords")
    suggested_knowledge: str = Field(..., description="Suggested EQF level for Knowledge ILO")
    suggested_skills: str = Field(..., description="Suggested EQF level for Skills ILO")
    suggested_ra: str = Field(..., description="Suggested EQF level for Responsibility and Autonomy ILO")


class GroqWrapper(BaseLLMWrapper):
    """LLM wrapper for the Groq API with shared round-robin key rotation."""

    def __init__(self, cfg: Dict):
        llm_cfg = cfg.get("llm_settings") or {}
        processing_cfg = llm_cfg.get("processing_llm", {})

        keys_str = os.environ.get("API_KEYS")
        if keys_str:
            api_keys = [k.strip() for k in keys_str.split(",") if k.strip()]
        else:
            single_key = os.environ.get("GROQ_API_KEY") or llm_cfg.get("api_key")
            api_keys = [single_key] if single_key else []

        if not api_keys:
            raise ValueError("Groq API keys not found. Set 'API_KEYS' env var.")

        _register_keys(api_keys)

        self.model_name = processing_cfg.get("model", "llama-3.3-70b-versatile")
        self.temperature = float(processing_cfg.get("temperature", 0.0))
        self.top_p = float(processing_cfg.get("top_p", 1.0))

        self.session_messages: List[Dict[str, str]] = []

    def reset_session(self):
        self.session_messages = []

    def run_prompt(self, prompt: str, mode: Optional[str] = None, remember: bool = True) -> Union[str, BaseModel]:
        output_model = None
        if mode == "criterion":
            output_model = CriterionEvaluation
        elif mode == "snapshot":
            output_model = DocumentSnapshot

        messages = [{"role": msg["role"], "content": msg["content"]} for msg in self.session_messages]

        if output_model:
            schema_json = json.dumps(output_model.model_json_schema(), indent=2)
            system_msg = (
                f"You are a helpful assistant. Output a JSON object strictly following this schema:\n{schema_json}"
            )
            if messages and messages[0]["role"] == "system":
                messages[0]["content"] += f"\n\n{system_msg}"
            else:
                messages.insert(0, {"role": "system", "content": system_msg})

        messages.append({"role": "user", "content": prompt})

        kwargs = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
            "top_p": self.top_p,
        }

        if output_model:
            kwargs["response_format"] = {"type": "json_object"}

        text_result = ""
        last_error = None

        for api_key in _next_key_rotation():
            try:
                client = _shared_clients[api_key]
                response = client.chat.completions.create(**kwargs)
                text_result = response.choices[0].message.content
                break
            except Exception as e:
                last_error = e
                logger.warning(f"Groq key {api_key[:8]}... failed: {e}")
                continue
        else:
            raise ValueError(f"All Groq API keys failed. Last error: {last_error}")

        if remember:
            self.session_messages.append({"role": "user", "content": prompt})
            self.session_messages.append({"role": "assistant", "content": text_result})

        if output_model:
            try:
                clean_text = text_result.replace("```json", "").replace("```", "").strip()
                validated = output_model.model_validate_json(clean_text)
                if mode == "snapshot":
                    return validated.model_dump_json(indent=2)
                return validated
            except (ValidationError, json.JSONDecodeError) as e:
                logger.error(f"Pydantic validation failed (mode={mode}): {e}")
                logger.debug(f"Raw LLM output: {text_result}")
                raise ValueError(f"Invalid JSON from Groq (mode={mode}): {e}")

        return text_result
