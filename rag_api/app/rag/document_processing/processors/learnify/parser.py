# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from .cleaning import clean_html, clean_text_block


def extract_texts_recursively(obj, sections, last_value=None, last_question=None):
    """
    Recursively extract and structure text, subtitles, and question-answer groups.
    Returns sections = [{'subtitle': ..., 'text': ...}, {'question': ..., 'answers': [...]}, ...]
    """

    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "question" and isinstance(v, str):
                last_question = clean_html(v)

            elif k == "answers" and isinstance(v, list):
                # Handle structured answers with correctness info
                for ans in v:
                    if isinstance(ans, dict) and "value" in ans:
                        val = clean_html(ans["value"])
                        if ans.get("correct", False):
                            val += " (Correct)"
                        if last_question:
                            if not sections or "question" not in sections[-1] or sections[-1]["question"] != last_question:
                                sections.append({"question": last_question, "answers": []})
                            sections[-1]["answers"].append(val)

            elif k in ("value",) and isinstance(v, str):
                val = clean_html(v)
                # If we're inside a question context, append as an answer
                if last_question:
                    if not sections or "question" not in sections[-1] or sections[-1]["question"] != last_question:
                        sections.append({"question": last_question, "answers": []})
                    sections[-1]["answers"].append(val)
                # Else treat as subtitle
                else:
                    last_value = val

            elif k == "body" and isinstance(v, str):
                text = clean_html(v)
                img_url = obj.get("image")

                if img_url and isinstance(img_url, str) and img_url.strip():
                    text += " [IMAGE]"

                sections.append({"subtitle": last_value, "text": text})
                last_value = None
                last_question = None

            elif isinstance(v, (dict, list)):
                last_value, last_question = extract_texts_recursively(v, sections, last_value, last_question)

    elif isinstance(obj, list):
        for item in obj:
            last_value, last_question = extract_texts_recursively(item, sections, last_value, last_question)
    return last_value, last_question


def extract_text_from_content(data: dict) -> dict:
    """Extract structured sections and Q&A from a Learnify content page payload."""

    contents = data.get("contents", {})
    title = contents.get("title", {}).get("en", "")
    scenarios = contents.get("scenario", [])
    sections = []
    video_links = []

    for scenario in scenarios:
        en = scenario.get("en", {})

        # Detect video blocks
        if en.get("type") == "video" and en.get("path"):
            video_links.append(en["path"])

        extract_texts_recursively(en, sections)

    # Clean final output
    for s in sections:
        if "subtitle" in s:
            s["subtitle"] = clean_text_block(s.get("subtitle", ""))
            s["text"] = clean_text_block(s.get("text", ""))
        if "question" in s:
            s["question"] = clean_text_block(s.get("question", ""))
            s["answers"] = [clean_text_block(a) for a in s.get("answers", [])]

    return {
        "id": contents.get("id"),
        "title": clean_text_block(title),
        "videos": video_links,
        "sections": [s for s in sections if any(s.values())],
    }
