import os
import json
import random
import threading
from groq import Groq
from typing import Optional, Union, Dict, List
from pydantic import BaseModel, Field, model_validator, ValidationError
from ..base import BaseLLMWrapper

# ---- Pydantic Model for Criterion Evaluation ----
class CriterionEvaluation(BaseModel):
    """Model for structured criterion evaluation output."""
    Name: str
    Shortcomings: list[str] = Field(..., description="List of shortcomings found")
    Recommendations: list[str] = Field(..., description="List of recommendations, one per shortcoming")
    Deductions: list[float] = Field(..., description="Numeric deductions matching each shortcoming")
    Description: str = Field(..., description="Summary of the overall analysis")

    @model_validator(mode="after")
    def check_lengths(cls, values):
        s, r, d = values.Shortcomings, values.Recommendations, values.Deductions
        if not (len(s) == len(r) == len(d)):
            raise ValueError(
                f"Mismatch in lengths: Shortcomings={len(s)}, Recommendations={len(r)}, Deductions={len(d)}"
            )
        return values

# ---- Pydantic Model for Document Snapshot ----
class DocumentSnapshot(BaseModel):
    Title: str = Field(..., description="Module title")
    Keywords: str = Field(..., description="Keywords as a single string")
    Abstract: str = Field(..., description="Abstract or 3-5 sentence summary")
    IntendedLearningOutcomesKnowledge: str = Field(..., description="Learning outcomes: Knowledge")
    IntendedLearningOutcomesSkills: str = Field(..., description="Learning outcomes: Skills")
    IntendedLearningOutcomesResponsibility: str = Field(..., description="Learning outcomes: Responsibility")
    Outline: list[str] = Field(..., description="Ordered list of major sections/headings")
    ImportantInformation: list[str] = Field(..., description="10-15 bullets covering main learning goals, scope, methods, and assessments")

class ModuleMetadata(BaseModel):
    """Model for extracting specific module metadata."""
    title: str = Field(..., description="The official title of the module")
    abstract: str = Field(..., description="Summary of the module content")
    uniqueness: str = Field(..., description="Explanation of what makes this module unique")
    societal_relevance: str = Field(..., description="How this module impacts society")
    elh: str = Field(..., description="Estimated Learning Hours (ELH) value")
    eqf: str = Field(..., description="European Qualification Framework (EQF) level")
    smcts: str = Field(..., description="SMCTS credit value")
    teachers: str = Field(..., description="Names and details of teachers/authors")
    keywords: str = Field(..., description="Comma-separated keywords")

# ---- Groq Wrapper ----
class GroqWrapper(BaseLLMWrapper):
    def __init__(self, cfg: Dict):
        llm_cfg = (cfg.get("llm_settings") or {})
        processing_cfg = llm_cfg.get("processing_llm", {})

        keys_str = os.environ.get("API_KEYS")
        if keys_str:
            self.api_keys = [k.strip() for k in keys_str.split(",") if k.strip()]
        else:
            single_key = os.environ.get("GROQ_API_KEY") or llm_cfg.get("api_key")
            self.api_keys = [single_key] if single_key else []
        
        if not self.api_keys:
            raise ValueError("Groq API keys not found. Set 'API_KEYS' env var.")

        random.shuffle(self.api_keys)
        self.current_key_index = 0
        self.lock = threading.Lock()

        self.model_name = processing_cfg.get("model", "llama-3.3-70b-versatile")
        self.temperature = float(processing_cfg.get("temperature", 0.0))
        
        self.session_messages: List[Dict[str, str]] = []

    def reset_session(self):
        self.session_messages = []

    def _get_ordered_keys(self):
        # Thread-safe Round Robin key selection.
        with self.lock:
            ordered = self.api_keys[self.current_key_index:] + self.api_keys[:self.current_key_index]
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            return ordered

    def run_prompt(self, prompt: str, mode: Optional[str] = None, remember: bool = True) -> Union[str, BaseModel]:
        
        output_model = None
        if mode == "criterion":
            output_model = CriterionEvaluation
        elif mode == "snapshot":
            output_model = DocumentSnapshot
        elif mode == "metadata": 
            output_model = ModuleMetadata

        # Prepare messages
        messages = [{"role": msg["role"], "content": msg["content"]} for msg in self.session_messages]
        
        # System Prompt Injection (Required for JSON Object mode)
        if output_model:
            schema_json = json.dumps(output_model.model_json_schema(), indent=2)
            system_msg = (
                f"You are a helpful assistant. Output a JSON object strictly following this schema:\n{schema_json}"
            )
            # Insert at start if no system message, else prepend
            if messages and messages[0]["role"] == "system":
                messages[0]["content"] += f"\n\n{system_msg}"
            else:
                messages.insert(0, {"role": "system", "content": system_msg})
        
        messages.append({"role": "user", "content": prompt})

        # Base params
        kwargs = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
        }

        # Force JSON Object mode
        if output_model:
            kwargs["response_format"] = {"type": "json_object"}

        text_result = ""
        last_error = None
        success = False

        keys_to_try = self._get_ordered_keys()

        for api_key in keys_to_try:
            try:
                client = Groq(api_key=api_key)
                response = client.chat.completions.create(**kwargs)
                
                text_result = response.choices[0].message.content
                success = True
                break 

            except Exception as e:
                last_error = e
                # Log error briefly and continue to next key
                print(f"Groq Key Error ({api_key[:8]}...): {e}")
                continue
        
        if not success:
             # Fallback: Raise error to be caught upstream
             raise ValueError(f"API Error (All keys failed): {last_error}")

        # Manage session
        if remember:
            self.session_messages.append({"role": "user", "content": prompt})
            self.session_messages.append({"role": "assistant", "content": text_result})

        # Validate output
        if output_model:
            try:
                clean_text = text_result.replace("```json", "").replace("```", "").strip()
                validated = output_model.model_validate_json(clean_text)
                
                if mode == "snapshot":
                    return validated.model_dump_json(indent=2)
                
                return validated

            except (ValidationError, json.JSONDecodeError) as e:
                print(f"Validation error ({mode}): {e}")
                print("Raw output:", text_result)
                raise ValueError(f"Invalid JSON from Groq: {e}")

        return text_result
