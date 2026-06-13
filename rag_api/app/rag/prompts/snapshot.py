# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

def build_snapshot_prompt(full_text: str) -> str:
    """
    Build the prompt that generates a structured document digest (snapshot).
    The LLM is instructed to extract — not summarize — key fields from the
    document text and return them as a JSON object. {full_text} is placed at
    the very end so prompt caching can reuse the stable prefix.
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

        "### REQUIRED OUTPUT FORMAT:\n"
        "{\n"
        '  "Title": "...",\n'
        '  "Keywords": ["keyword1", "keyword2"],\n'
        '  "Abstract": "...",\n'
        '  "IntendedLearningOutcomesKnowledge": "...",\n'
        '  "IntendedLearningOutcomesSkills": "...",\n'
        '  "IntendedLearningOutcomesResponsibility": "...",\n'
        '  "Outline": ["Section 1 title", "Section 2 title", "..."],\n'
        '  "ImportantInformation": ["Verbatim sentence 1", "Verbatim sentence 2", "...", "Up to 7"]\n'
        "}\n\n"

        "DO NOT ADD ANY TEXT THAT IS NOT DIRECTLY FOUND IN THE DOCUMENT CONTENT BELOW.\n\n"

        f"### DOCUMENT CONTENT:\n{full_text}"
    )
