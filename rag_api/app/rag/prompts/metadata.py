# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

def build_metadata_prompt(context_text: str) -> str:
    """
    Build the prompt for extracting basic module metadata fields.
    Extracts title, abstract, uniqueness, societal relevance, ELH, EQF,
    SMCTS, teachers, and keywords as a JSON object.
    """

    return (
        "You are a strict metadata extractor. Extract educational attributes from the document text below.\n"
        "Return ONLY a valid JSON object. Do not use markdown tags like ```json.\n\n"

        "### REQUIRED JSON KEYS & FORMATS:\n"
        "- title: The main title of the module (String).\n"
        "- abstract: The Abstract section (String).\n"
        "- uniqueness: The Uniqueness section (String).\n"
        "- societal_relevance: The Societal Relevance section (String).\n"
        "- elh: Estimated Learning Hours (String, e.g., '4').\n"
        "- eqf: European Qualification Framework level (String, e.g., '5').\n"
        "- smcts: Stackable Master Credit value (String, e.g., '0.14').\n"
        "- teachers: Authors, Teachers, or Instructors mentioned (String, e.g., 'Dr. John Doe, Prof. John Doe').\n"
        "- keywords: The Keywords section (JSON Array of strings, e.g., [\"Keyword 1\", \"Keyword 2\", \"Keyword 3\"]).\n\n"

        "### RULES:\n"
        "1. Extract values exactly as they appear.\n"
        "2. If a string field is not found, return 'N/A'.\n"
        "3. If the keywords field is not found, return an empty array [].\n\n"

        f"### DOCUMENT CONTENT:\n{context_text}"
    )


def build_eqf_prompt(context_text: str, eqf_guideline_text: str) -> str:
    """
    Build the prompt for assigning EQF levels to individual ILOs.
    The LLM matches action verbs in each ILO (Knowledge, Skills, Responsibility)
    against the provided EQF guideline and returns suggested levels. The
    guideline text is loaded from a static KB file (identical across all calls)
    so it lives in the stable prefix; only {context_text} breaks the cache.
    """

    return (
        "You are a strict academic evaluator. IGNORE the overall course EQF value. "
        "Your task is to assign European Qualification Framework (EQF) levels to specific Intended Learning Outcomes (ILOs).\n"
        "Return ONLY a valid JSON object. Do not use markdown tags like ```json.\n\n"

        "### REQUIRED JSON KEYS (in exact order):\n"
        "- knowledge_evidence: Exact quote of the 'Knowledge' ILO from the text. If not found, write 'None'.\n"
        "- suggested_knowledge: The EQF level determined ONLY by matching the verbs in 'knowledge_evidence' against the guideline. Append ' (AI GENERATED)' if suggestion is made.\n"
        "- skills_evidence: Exact quote of the 'Skills' ILO from the text. If not found, write 'None'.\n"
        "- suggested_skills: The EQF level determined ONLY by matching the verbs in 'skills_evidence' against the guideline. Append ' (AI GENERATED)' if suggestion is made.\n"
        "- ra_evidence: Exact quote of the 'Responsibility and Autonomy' ILO from the text. If not found, write 'None'.\n"
        "- suggested_ra: The EQF level determined ONLY by matching the verbs in 'ra_evidence' against the guideline. Append ' (AI GENERATED)' if suggestion is made.\n\n"

        "### CRITICAL RULES:\n"
        "1. IGNORE the overall course EQF value. ILOs often have lower or different levels than the global course.\n"
        "2. If the evidence is 'None', the suggested level MUST be 'N/A'.\n"
        "3. Base your decision purely on the verbs in the evidence vs the provided guideline.\n\n"

        f"### EQF LEVELS GUIDELINE:\n{eqf_guideline_text}\n\n"

        f"### DOCUMENT CONTENT:\n{context_text}"
    )
