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

        text = "" # Define text in the outer scope
        try:
            response = self.model.generate_content(
                gemini_history,
                generation_config=generation_config,
                tools=tools_list, 
                tool_config=tool_config
            )
            
            if not response.candidates:
                 raise ValueError("No candidates returned from Gemini.")
            
            if not response.candidates[0].content.parts or not response.candidates[0].content.parts[0].function_call:
                # The model returned raw text instead of a tool call
                text = response.text if response.text else "API Error: Model did not use the required tool."
                raise ValueError(text) # Jump to 'except'

            func_call = response.candidates[0].content.parts[0].function_call
            args_dict = type(func_call).to_dict(func_call)['args']
            
            text = json.dumps(args_dict) # This is the successful JSON string

        except Exception as e:
            print(f"Error calling Gemini API or parsing tool call: {e}")
            
            # --- YOUR SUGGESTED FIX ---
            # The error 'e' is a ValueError containing the raw text. Try to parse it.
            error_text = str(e) 
            if output_model:
                try:
                    # Try to parse the error text as JSON
                    validated = output_model.model_validate_json(error_text)
                    
                    # It worked! The error was just the model returning text
                    print("--- [INFO] Successfully recovered JSON from raw text output. ---")

                    # Print the raw output
                    print("-------------------- Raw Model Output (Gemini Text Fallback) --------------------")
                    print(error_text)
                    print("-----------------------------------------------------------------------------")

                    # Manage session
                    if remember:
                        self.session_messages.append({"role": "user", "content": prompt})
                        self.session_messages.append({"role": "assistant", "content": error_text})

                    # Now, return the correct format
                    if mode == "snapshot":
                        return validated.model_dump_json(indent=2)
                    return validated # Return the Pydantic OBJECT

                except (ValidationError, json.JSONDecodeError):
                    # It wasn't valid JSON, so it's a real error.
                    print("--- [ERROR] Raw text output was not valid JSON. ---")
                    # Fall through to returning the error string
                    text = error_text # This will be the string that causes the crash
                    return text
            # --- END OF FIX ---

            # Fallback for real API errors
            try:
                text = f"API Error: {response.prompt_feedback}"
            except Exception:
                text = f"API Error: {error_text}"
            return text # This is the STRING that causes the crash

        
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
                return text # This is the STRING that causes the crash

        return text