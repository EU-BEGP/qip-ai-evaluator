# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from typing import Optional


def extract_learnify_code(input_str: str) -> Optional[str]:
    """
    Extract the clean course code from a full Learnify URL or bare code.

    Handles:
    - https://time.learnify.se/l/show.html#att/OYJPG  -> OYJPG
    - https://time.learnify.se/l/show.html#qx5Ay      -> qx5Ay
    - https://time.learnify.se/l/show.html#att/OYJPG?lang=en -> OYJPG
    - OYJPG -> OYJPG
    """
    
    if not input_str:
        return None

    input_str = input_str.strip()

    # Isolate fragment (everything after last '#')
    if "#" in input_str:
        code_part = input_str.split("#")[-1]
    else:
        code_part = input_str

    # Remove 'att/' prefix for legacy/standard links
    if code_part.startswith("att/"):
        code_part = code_part[4:]

    # Remove query parameters
    if "?" in code_part:
        code_part = code_part.split("?")[0]

    return code_part.strip().strip("/")
