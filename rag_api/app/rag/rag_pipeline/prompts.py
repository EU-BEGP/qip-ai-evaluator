# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import json
from typing import Dict


def build_snapshot_prompt(full_text: str) -> str:
    """
    Build the prompt that generates a structured document digest (snapshot).

    The LLM is instructed to extract — not summarize — key fields from the
    document text and return them as a JSON object.
    """

    return (
        "You are an **academic text parser** — not a summarizer, writer, or analyst.\n"
        "Your ONLY task is to EXTRACT text segments from the DOCUMENT CONTENT below and place them into a JSON object that follows the DocumentSnapshot schema.\n\n"
        "### HARD RULES:\n"
        "1. Return **ONLY JSON** — no reasoning, no explanation, no <think> blocks.\n"
        "2. **Copy text EXACTLY as it appears** in the document. Do not infer, interpret, or guess missing parts.\n"
        "3. If something does not appear in the document, leave it empty (\"\" or []).\n"
        "4. The 'Outline' field must list all main titles and subtitles IN THE DOCUMENT, word-for-word, in order.\n"
        "5. The 'ImportantInformation' field must contain verbatim sentences or short verbatim phrases "
        "copied directly from the document — no paraphrasing, no summarizing, no rewording.\n"
        "6. Never add, reformulate, or assume information. Do not include anything that isn't literally in the document.\n"
        "7. Output must be syntactically valid JSON only.\n\n"
        f"### DOCUMENT CONTENT:\n{full_text}\n\n"
        "### REQUIRED OUTPUT FORMAT:\n"
        "{\n"
        '  "Title": "...",\n'
        '  "Keywords": ["..."],\n'
        '  "Abstract": "...",\n'
        '  "IntendedLearningOutcomesKnowledge": "...",\n'
        '  "IntendedLearningOutcomesSkills": "...",\n'
        '  "IntendedLearningOutcomesResponsibility": "...",\n'
        '  "Outline": ["Title 1", "Subtitle 1.1", "Subtitle 1.2", "..."],\n'
        '  "ImportantInformation": ["Verbatim sentence 1", "Verbatim sentence 2", "...", "Up to 7"]\n'
        '  "elh": "...",\n'
        '  "eqf": "...",\n'
        "}\n\n"
        "DO NOT ADD ANY TEXT THAT IS NOT DIRECTLY FOUND IN THE DOCUMENT CONTENT ABOVE."
    )


def build_evaluation_prompt(criterion: Dict, doc_text: str, kb_text: str,
                             document_snapshot: str, previous_eval_section: str = "") -> str:
    """
    Build the prompt for evaluating a single criterion against document and KB chunks.

    Scoring starts at 5.0; the LLM subtracts partial points for each shortcoming.
    Each shortcoming requires exactly one recommendation and one numeric deduction.
    """

    return (
        "You are an EXPERT AND CONFIDENT academic evaluator.\n"
        "DO NOT TAKE POINTS UNLESS THERE IS A CLEAR REASON. DO NOT MAKE STRONG DEDUCTIONS.\n"
        "Do not deduct points for minor issues or ambiguities if the core concept is present.\n"
        "Evaluate the DOCUMENT against the criterion STRICTLY and ONLY using the RUBRIC.\n\n"

        "### CONTEXT INTERPRETATION:\n"
        "- The 'DOCUMENT SNAPSHOT' is a silent helper only — do NOT mention 'Snapshot' or 'Knowledge Base' in your output.\n"
        "- If you find information in the Snapshot, treat it as found directly in the Document.\n\n"

        "### REQUIRED OUTPUT — MANDATORY RULES:\n"
        "Return ONLY a valid JSON object with EXACTLY these 5 keys (exact names, exact types):\n\n"
        '  "Name"            string   — the criterion name\n'
        '  "Shortcomings"    array of strings — plain text only, NEVER numbers or nested lists\n'
        '  "Recommendations" array of strings — plain text only, NEVER numbers or nested lists\n'
        '  "Deductions"      array of numbers — negative floats only (e.g. -0.5), NEVER positive numbers, NEVER text or lists\n'
        '  "Description"     string   — concise summary of the full analysis\n\n'

        "CRITICAL: Shortcomings, Recommendations, and Deductions MUST have IDENTICAL length.\n"
        "  Index i must correspond: Shortcomings[i] ↔ Recommendations[i] ↔ Deductions[i]\n"
        "  Deductions must be NEGATIVE numbers (e.g. -0.5, -1.0). Never use positive values.\n"
        "  Sum of all Deductions must not exceed -5.0 in total. Maximum score is 5.0, minimum is 0.0.\n"
        "  Putting numbers inside Recommendations or text inside Deductions causes task failure.\n\n"

        "### EXAMPLE — with shortcomings:\n"
        "{\n"
        '  "Name": "Assessment Design",\n'
        '  "Shortcomings": ["Missing formative assessments", "No grading rubric provided"],\n'
        '  "Recommendations": ["Add at least 2 formative checkpoints", "Include a grading rubric with criteria"],\n'
        '  "Deductions": [-0.5, -1.0],\n'
        '  "Description": "The module lacks formative assessments and does not provide grading criteria."\n'
        "}\n\n"

        "### EXAMPLE — no shortcomings (perfect score):\n"
        "{\n"
        '  "Name": "Assessment Design",\n'
        '  "Shortcomings": ["NO SHORTCOMINGS"],\n'
        '  "Recommendations": ["NO RECOMMENDATIONS"],\n'
        '  "Deductions": [0.0],\n'
        '  "Description": "The module fully meets all requirements for this criterion."\n'
        "}\n\n"

        "### EVALUATION INSTRUCTIONS:\n"
        "1. Read the CRITERION and DOCUMENT carefully. Find the relevant sections in the document.\n"
        "2. Start from 5.0 and subtract partial points for each shortcoming found.\n"
        "3. For EACH shortcoming: one Recommendation (text) and one Deduction (negative number).\n"
        "4. Use proportional deductions depending on severity:\n"
        "   - Minor issue: 0.1 - 0.5 points\n"
        "   - Moderate issue: 0.5 - 1 points\n"
        "   - Major issue: up to 4 points\n"
        "5. Be lenient: if the document mostly satisfies the criterion, apply only small deductions.\n"
        "6. If no shortcomings exist, use the no-shortcomings example above exactly.\n"
        "7. Finish with a Description string summarizing the analysis.\n\n"

        f"### Criterion:\n{json.dumps(criterion, indent=2)}\n\n"
        f"### DOCUMENT:\n{doc_text}\n\n"
        f"### KNOWLEDGE BASE:\n{kb_text}\n\n"
        f"### DOCUMENT SNAPSHOT:\n{document_snapshot}\n\n"
        f"{previous_eval_section}"
    )


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
    against the provided EQF guideline and returns suggested levels.
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
        f"### DOCUMENT CONTENT:\n{context_text}\n\n"
        f"### EQF LEVELS GUIDELINE:\n{eqf_guideline_text}\n\n"
        "### CRITICAL RULES:\n"
        "1. IGNORE the overall course EQF value. ILOs often have lower or different levels than the global course.\n"
        "2. If the evidence is 'None', the suggested level MUST be 'N/A'.\n"
        "3. Base your decision purely on the verbs in the evidence vs the provided guideline."
    )
