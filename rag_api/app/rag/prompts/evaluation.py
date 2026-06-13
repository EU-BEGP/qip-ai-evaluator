# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import json
from typing import Dict, List, Optional


_BREVITY_RULE = (
    "5. Keep each Description, shortcoming, and recommendation concise and precise — "
    "aim for a soft limit of about 30 words each.\n\n"
)

_SCORING_RULES = (
    "SCORING:\n"
    "Start from 5.0 and subtract deductions.\n"
    "Minor: -0.1 to -0.5\n"
    "Moderate: -0.5 to -1.0\n"
    "Major: up to -4.0\n\n"
)

# Always-on note that lives in the stable prefix so prompt caching is not broken
# by per-call conditional language about which helper sections are present.
_HELPERS_NOTE = (
    "NOTE: The DOCUMENT SNAPSHOT and KNOWLEDGE BASE sections (when populated below) "
    "are helpers — supporting context only. Do not mention them in your output.\n\n"
)

_BATCH_OUTPUT_EXAMPLE = (
    "EXAMPLE OUTPUT (study this exact shape — empty Issues means no deficiencies):\n"
    "{\n"
    '  "evaluations": [\n'
    "    {\n"
    '      "Name": "Example Criterion A",\n'
    '      "Description": "Title is generic and underdescribes module focus.",\n'
    '      "Issues": [\n'
    "        {\n"
    '          "shortcoming": "Title does not reflect the robotics focus.",\n'
    '          "recommendation": "Use a descriptive title such as \'Dobot E6 Lab: Remote Operation\'.",\n'
    '          "deduction": 0.5\n'
    "        }\n"
    "      ]\n"
    "    },\n"
    "    {\n"
    '      "Name": "Example Criterion B",\n'
    '      "Description": "Keywords are adequate.",\n'
    '      "Issues": []\n'
    "    }\n"
    "  ]\n"
    "}\n\n"
)

_SINGLE_OUTPUT_EXAMPLE = (
    "EXAMPLE OUTPUT (study this exact shape — empty Issues means no deficiencies):\n"
    "{\n"
    '  "Name": "Example Criterion",\n'
    '  "Description": "Title is generic.",\n'
    '  "Issues": [\n'
    "    {\n"
    '      "shortcoming": "Title does not reflect module focus.",\n'
    '      "recommendation": "Use a more descriptive title.",\n'
    '      "deduction": 0.5\n'
    "    }\n"
    "  ]\n"
    "}\n\n"
)

_SNAPSHOT_EMPTY_PLACEHOLDER = (
    "(full-module mode — no snapshot generated; the DOCUMENT section below contains the entire module)"
)
_KB_EMPTY_PLACEHOLDER = "(no KB context for this query)"


def _snapshot_block(document_snapshot: str) -> str:
    content = document_snapshot.strip() if document_snapshot else _SNAPSHOT_EMPTY_PLACEHOLDER
    return f"### DOCUMENT SNAPSHOT:\n{content}\n\n"


def _kb_block(kb_text: str) -> str:
    content = kb_text.strip() if kb_text else _KB_EMPTY_PLACEHOLDER
    return f"### KNOWLEDGE BASE:\n{content}\n\n"


def _find_criterion_in_history(prev_eval_json: Optional[Dict], scan_name: str, criterion_name: str) -> Optional[Dict]:
    """Search a previous evaluation JSON for a specific criterion's data."""

    if not prev_eval_json or "content" not in prev_eval_json:
        return None
    for scan_data in prev_eval_json.get("content", []):
        if scan_data.get("scan") == scan_name:
            for crit_data in scan_data.get("criteria", []):
                if crit_data.get("name") == criterion_name:
                    return crit_data
    return None


def build_previous_eval_section(previous_evaluation: Optional[Dict], scan_name: str,
                                criterion_name: str) -> str:
    """Build the previous-evaluation context block injected into evaluation prompts."""

    if not (previous_evaluation and scan_name and criterion_name):
        return ""
    prev = _find_criterion_in_history(previous_evaluation, scan_name, criterion_name)
    if not prev:
        return ""
    return (
        f"### PREVIOUS EVALUATION TO '{criterion_name}' IN THE MODULE (most recent):\n"
        f"Description: {prev.get('description', '')}\n"
        f"Score: {prev.get('score', 0.0)}\n"
        f"Shortcomings: {prev.get('shortcomings', [])}\n"
        f"Recommendations: {prev.get('recommendations', [])}\n\n"
    )


def build_evaluation_prompt(criterion: Dict, doc_text: str, kb_text: str,
                            document_snapshot: str, previous_eval_section: str = "") -> str:
    """
    Build the prompt for evaluating a single criterion against document and KB chunks.
    Scoring starts at 5.0; the LLM subtracts partial points for each shortcoming.
    Each shortcoming requires exactly one recommendation and one numeric deduction.
    Ordered for prompt caching — stable header, then module-stable snapshot,
    then per-batch KB/document/criterion content at the tail.
    """

    return (
        # ---------- Stable prefix (cacheable) ----------
        "You are an expert academic evaluator.\n"
        "Evaluate the DOCUMENT against the CRITERION using the RUBRIC.\n"
        "Be fair and AVOID STRONG DEDUCTIONS unless clearly justified.\n\n"

        "RULES:\n"
        "1. Output ONE JSON object with keys: Name (string), Description (string), Issues (array).\n"
        "2. Each item in Issues is an object with: shortcoming (string), recommendation (string addressing that shortcoming), deduction (number).\n"
        "3. If the criterion is fully satisfied, return Issues as an empty array []. Do NOT invent placeholder issues.\n"
        "4. Recommendations are for fixing shortcomings — NEVER use them for praise or 'nice to have' suggestions.\n\n"

        + _BREVITY_RULE
        + _SCORING_RULES
        + _HELPERS_NOTE
        + _SINGLE_OUTPUT_EXAMPLE

        # ---------- Module-stable ----------
        + _snapshot_block(document_snapshot)

        # ---------- Volatile tail ----------
        + _kb_block(kb_text)
        + f"### DOCUMENT:\n{doc_text}\n\n"
        + f"### CRITERION:\n{json.dumps(criterion, indent=2)}\n\n"
        + previous_eval_section
    )


def build_batch_evaluation_prompt(criteria_batch: List[Dict], doc_text: str, kb_text: str,
                                  document_snapshot: str, prev_sections: List[str]) -> str:
    """
    Build prompt for evaluating N criteria in a single LLM call.
    Returns a JSON object {"evaluations": [...]} with one CriterionEvaluation per criterion.
    Ordered for prompt caching — stable header, then module-stable snapshot,
    then per-batch KB/document/criteria-blocks at the tail. Per-criterion
    previous_eval sections are stitched into the criteria blocks at the very end.
    """

    n = len(criteria_batch)

    criteria_blocks = []
    for i, (crit, prev) in enumerate(zip(criteria_batch, prev_sections), 1):
        block = f"--- Criterion {i}: {crit['name']} ---\n{json.dumps(crit, indent=2)}"
        if prev:
            block += f"\n{prev}"
        criteria_blocks.append(block)

    return (
        # ---------- Stable prefix (cacheable) ----------
        f"You are an expert academic evaluator.\n"
        f"Evaluate the DOCUMENT against each of the {n} criteria listed below.\n"
        f"Be fair and AVOID STRONG DEDUCTIONS unless clearly justified.\n\n"

        f"RULES:\n"
        f'1. Output ONE JSON object with key "evaluations" — an array with one entry per criterion, in the SAME ORDER as listed.\n'
        f"2. Each entry: Name (string), Description (string summary), Issues (array — empty [] if criterion is fully satisfied; do NOT invent placeholder issues).\n"
        f"3. Each item in Issues is an object: shortcoming (string), recommendation (string addressing that shortcoming), deduction (number).\n"
        f"4. Recommendations are for fixing shortcomings — NEVER use them for praise or 'nice to have' suggestions.\n\n"

        + _BREVITY_RULE
        + _SCORING_RULES
        + _HELPERS_NOTE
        + _BATCH_OUTPUT_EXAMPLE

        # ---------- Module-stable ----------
        + _snapshot_block(document_snapshot)

        # ---------- Volatile tail ----------
        + _kb_block(kb_text)
        + f"### DOCUMENT:\n{doc_text}\n\n"
        + f"### CRITERIA TO EVALUATE:\n\n"
        + "\n\n".join(criteria_blocks)
    )
