import re
from ollama import Client
from pydantic import BaseModel, Field, ValidationError, model_validator
from typing import List, Dict, Union, Optional
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
        """Ensure Shortcomings, Recommendations, and Deductions lists have equal lengths."""
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

# ---- Ollama Wrapper ----
class OllamaWrapper(BaseLLMWrapper):
    def __init__(self, cfg: dict):
        llm_cfg = (cfg.get("llm_settings") or {}).get("processing_llm", {})
        self.client = Client()
        self.llm_model = llm_cfg.get("model", "qwen2:7b")
        self.temperature = llm_cfg.get("temperature", 0.0)
        self.context_size = llm_cfg.get("context_size", 4096)
        self.session_messages: list[dict] = []

    def reset_session(self):
        self.session_messages = []

    def run_prompt(self, prompt: str, mode: Optional[str] = None, remember: bool = True) -> Union[str, BaseModel]:
        eval_options = {"temperature": float(self.temperature), "num_ctx": self.context_size}

        # Elegir modelo de salida y formato
        output_model = None
        json_format = None
        if mode == "criterion":
            output_model = CriterionEvaluation
            json_format = CriterionEvaluation.model_json_schema()
        elif mode == "snapshot":
            output_model = DocumentSnapshot
            json_format = DocumentSnapshot.model_json_schema()

        messages = self.session_messages + [{"role": "user", "content": prompt}]

        # ---- Llamada al cliente con formato ----
        response = self.client.chat(
            model=self.llm_model,
            messages=messages,
            format=json_format,
            options=eval_options,
            think=False,
            stream=False
        )

        text = re.sub(r"<think>.*?</think>", "", response.message.content, flags=re.DOTALL).strip()

        if remember:
            self.session_messages.append({"role": "user", "content": prompt})
            self.session_messages.append({"role": "assistant", "content": text})

        if output_model:
            try:
                validated = output_model.model_validate_json(text)
                
                if mode == "snapshot":
                    # For snapshot, return the JSON STRING
                    return validated.model_dump_json(indent=2)
                
                # For criterion, return the OBJECT for processing
                return validated
            
            except ValidationError as e:
                print(f"Validation error ({mode}):", e)
                print("Raw output:", text)
                return text

        return text
