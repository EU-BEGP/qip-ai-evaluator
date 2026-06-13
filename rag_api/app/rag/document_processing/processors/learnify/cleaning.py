# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import re
from bs4 import BeautifulSoup


def clean_html(html: str) -> str:
    """Convert HTML to readable plain text."""

    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")

    for img in soup.find_all("img"):
        img.replace_with("[IMAGE] ")

    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_text_block(text: str) -> str:
    """Normalize whitespace and line breaks."""

    if not text:
        return ""
    text = re.sub(r"\n+", "\n", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
