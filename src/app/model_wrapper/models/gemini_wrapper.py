import google.generativeai as genai
from pydantic import BaseModel, Field, ValidationError, model_validator
from typing import Union, Optional
from ..base import BaseLLMWrapper
import json
import os
import random
import threading

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

# ---- Gemini Wrapper ----
class GeminiWrapper(BaseLLMWrapper):
    def __init__(self, cfg: dict):
        llm_cfg = (cfg.get("llm_settings") or {})
        gemini_cfg = llm_cfg.get("processing_llm", {})
        
        # --- KEY ROTATION SETUP ---
        keys_str = os.environ.get("GEMINI_API_KEYS")
        if keys_str:
            # Format: "KEY1,KEY2,KEY3"
            self.api_keys = [k.strip() for k in keys_str.split(",") if k.strip()]
        else:
            # Fallback to single key
            single_key = llm_cfg.get("api_key")
            self.api_keys = [single_key] if single_key else []

        if not self.api_keys:
            raise ValueError("Gemini API key not found (checked GEMINI_API_KEYS and config)")
            
        # Shuffle once at startup so workers don't all start on Key 1
        random.shuffle(self.api_keys)
        self.current_key_index = 0
        self.lock = threading.Lock()
        # --------------------------

        self.model_name = gemini_cfg.get("model", "gemini-1.5-flash")
        self.temperature = float(gemini_cfg.get("temperature", 0.0))
        self.top_p = float(gemini_cfg.get("top_p", 1.0))
        
        # Model is initialized per-request now
        self.session_messages: list[dict] = []

    def reset_session(self):
        self.session_messages = []

    def _get_ordered_keys(self):
        """Get keys starting from current index (Round Robin)."""
        with self.lock:
            ordered = self.api_keys[self.current_key_index:] + self.api_keys[:self.current_key_index]
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            return ordered

    def run_prompt(self, prompt: str, mode: Optional[str] = None, remember: bool = True) -> Union[str, BaseModel]:
        
        output_model = None
        tools_list = None
        
        if mode == "criterion":
            output_model = CriterionEvaluation
            tools_list = [CriterionEvaluation]
        elif mode == "snapshot":
            output_model = DocumentSnapshot
            tools_list = [DocumentSnapshot]
        elif mode == "metadata": 
            output_model = ModuleMetadata
            tools_list = [ModuleMetadata]

        generation_config = genai.types.GenerationConfig(
            temperature=self.temperature,
            top_p=self.top_p
        )
        
        # --- FORCE JSON MODE (ANY) ---
        tool_config = {
            "function_calling_config": {
                "mode": "ANY", 
                "allowed_function_names": [output_model.__name__] if output_model else []
            }
        }
        if not output_model:
            tool_config = None

        gemini_history = []
        for msg in self.session_messages:
            role = "model" if msg["role"] == "assistant" else "user"
            gemini_history.append({"role": role, "parts": [msg["content"]]})
        
        gemini_history.append({"role": "user", "parts": [prompt]})

        text_result = ""
        last_error = None
        success = False
        
        # --- KEY ROTATION LOOP ---
        keys_to_try = self._get_ordered_keys()

        for api_key in keys_to_try:
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel(self.model_name)

                response = model.generate_content(
                    gemini_history,
                    generation_config=generation_config,
                    tools=tools_list, 
                    tool_config=tool_config
                )
                
                if not response.candidates:
                     raise ValueError("No candidates returned from Gemini.")
                
                # Check if blocked by safety/recitation (Finish Reason 10)
                if response.candidates[0].finish_reason == 10: 
                     raise ValueError(f"Gemini refused: Recitation/Safety check failed.")

                if output_model:
                    if not response.candidates[0].content.parts or not response.candidates[0].content.parts[0].function_call:
                        # Try grabbing text for debug/fallback
                        raw = ""
                        try: raw = response.candidates[0].content.parts[0].text 
                        except: pass
                        raise ValueError(f"Model did not use required tool. Raw: {raw}")

                    func_call = response.candidates[0].content.parts[0].function_call
                    args_dict = type(func_call).to_dict(func_call)['args']
                    text_result = json.dumps(args_dict)
                else:
                    if response.candidates[0].content.parts:
                        text_result = response.candidates[0].content.parts[0].text
                
                success = True
                break # Exit loop on success

            except Exception as e:
                last_error = e
                error_str = str(e)
                # If safety error, rotation won't help. Stop.
                if "Recitation" in error_str or "Safety" in error_str:
                    break
                # If other error (Quota/Network), continue to next key
                continue
        
        # --- END ROTATION LOOP ---

        if not success:
            print(f"All keys failed. Last error: {last_error}")
            
            # --- FALLBACK LOGIC (Recover JSON from error) ---
            error_str = str(last_error)
            recovered = False
            
            if output_model:
                if "{" in error_str and "}" in error_str:
                    try:
                        start = error_str.find("{")
                        end = error_str.rfind("}") + 1
                        json_candidate = error_str[start:end]
                        validated = output_model.model_validate_json(json_candidate)
                        print("--- [INFO] Successfully recovered JSON from error message. ---")
                        text_result = json_candidate
                        recovered = True
                    except:
                        pass
            
            if not recovered:
                # Return error string to let evaluator fail gracefully
                return f"API Error: {last_error}"

        
        print("-------------------- Raw Model Output (Gemini Tool Call) --------------------")
        print(text_result)
        print("-------------------------------------------------------------------------")

        # 6. Manage session
        if remember:
            self.session_messages.append({"role": "user", "content": prompt})
            self.session_messages.append({"role": "assistant", "content": text_result})

        # 7. Validate output
        if output_model:
            try:
                validated = output_model.model_validate_json(text_result)
                
                if mode == "snapshot":
                    return validated.model_dump_json(indent=2)
                
                return validated
            
            except ValidationError as e:
                print(f"Validation error ({mode}):", e)
                print("Raw output:", text_result)
                return text_result

        return text_result
