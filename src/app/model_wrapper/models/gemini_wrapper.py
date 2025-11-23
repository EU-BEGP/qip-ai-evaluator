import google.generativeai as genai
from pydantic import BaseModel, Field, ValidationError, model_validator
from typing import List, Dict, Union, Optional
from ..base import BaseLLMWrapper
import json  # <-- Import json

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

# ---- Gemini Wrapper ----
class GeminiWrapper(BaseLLMWrapper):
    def __init__(self, cfg: dict):
        llm_cfg = (cfg.get("llm_settings") or {})
        gemini_cfg = llm_cfg.get("processing_llm", {})
        
        # 1. Configure API Key
        api_key = llm_cfg.get("api_key")
        if not api_key:
            raise ValueError("Gemini API key not found in 'llm_settings.api_key'")
        genai.configure(api_key=api_key)

        # 2. Set Model and Temperature
        self.model_name = gemini_cfg.get("model", "gemini-1.5-flash")
        self.temperature = float(gemini_cfg.get("temperature", 0.0))
        self.top_p = float(gemini_cfg.get("top_p", 1.0))
        
        # 3. Initialize Model
        self.model = genai.GenerativeModel(self.model_name)
        
        # 4. Session History
        self.session_messages: list[dict] = []

    def reset_session(self):
        self.session_messages = []

    def run_prompt(self, prompt: str, mode: Optional[str] = None, remember: bool = True) -> Union[str, BaseModel]:
        
        output_model = None
        tools_list = None
        
        if mode == "criterion":
            output_model = CriterionEvaluation
            tools_list = [CriterionEvaluation]
        elif mode == "snapshot":
            output_model = DocumentSnapshot
            tools_list = [DocumentSnapshot]

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

        text = "" 
        try:
            response = self.model.generate_content(
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
                # Check for function call existence safely
                if not response.candidates[0].content.parts or not response.candidates[0].content.parts[0].function_call:
                    raw_text = ""
                    try:
                        if response.candidates[0].content.parts:
                            raw_text = response.candidates[0].content.parts[0].text
                    except: pass
                    raise ValueError(f"Model did not use required tool. Raw: {raw_text}")

                func_call = response.candidates[0].content.parts[0].function_call
                args_dict = type(func_call).to_dict(func_call)['args']
                text = json.dumps(args_dict)
            else:
                # Normal text mode
                if response.candidates[0].content.parts:
                    text = response.candidates[0].content.parts[0].text

        except Exception as e:
            print(f"Error calling Gemini API or parsing tool call: {e}")
            
            # --- FALLBACK LOGIC ---
            # Intentamos recuperar JSON del mensaje de error o del texto crudo si existe
            error_str = str(e)
            recovered = False
            
            if output_model:
                # 1. Buscar JSON dentro del mensaje de error (común en Valid Head/Toxic Tail)
                if "{" in error_str and "}" in error_str:
                    try:
                        start = error_str.find("{")
                        end = error_str.rfind("}") + 1
                        json_candidate = error_str[start:end]
                        
                        # Validar si es el JSON correcto
                        validated = output_model.model_validate_json(json_candidate)
                        
                        # Si pasamos aqui, se recuperó con éxito
                        print("--- [INFO] Successfully recovered JSON from error message. ---")
                        text = json_candidate
                        recovered = True
                    except:
                        pass
            
            if not recovered:
                # Fallback final para errores reales de API
                try:
                    text = f"API Error: {response.prompt_feedback}"
                except Exception:
                    text = f"API Error: {error_str}"
                return text # Retorna el error string (que causará fallo controlado en el evaluador)

        
        print("-------------------- Raw Model Output (Gemini Tool Call) --------------------")
        print(text)
        print("-------------------------------------------------------------------------")

        # 6. Manage session
        if remember:
            self.session_messages.append({"role": "user", "content": prompt})
            self.session_messages.append({"role": "assistant", "content": text})

        # 7. Validate output
        if output_model:
            try:
                validated = output_model.model_validate_json(text)
                
                if mode == "snapshot":
                    return validated.model_dump_json(indent=2)
                
                return validated
            
            except ValidationError as e:
                print(f"Validation error ({mode}):", e)
                print("Raw output:", text)
                return text

        return text
