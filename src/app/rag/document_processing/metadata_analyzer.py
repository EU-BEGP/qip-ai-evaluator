# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import re
from typing import Any, List, Tuple


class MetadataAnalyzer:
    """
    Locates the Module/Chapter section within a document chunk list and
    extracts the context text up to the next top-level header.
    """

    def _get_target_context(self, documents: List[Any]) -> Tuple[str, int]:
        if not documents:
            return "", -1

        module_start_idx = -1
        for i, doc in enumerate(documents):
            if hasattr(doc, 'metadata') and doc.metadata.get("is_first_module_section", False):
                module_start_idx = i
                break

        if module_start_idx == -1:
            return "", -1

        target_docs = documents[module_start_idx:]
        full_text = "".join(doc.page_content + "\n" for doc in target_docs)
        matches = list(re.finditer(r'(?m)^(#+)\s+(.+)$', full_text))

        found_h2 = False
        cut_off_pos = len(full_text)

        for match in matches:
            header_level = match.group(1).strip()
            if header_level == "##":
                found_h2 = True
            elif header_level == "#" and found_h2:
                cut_off_pos = match.start()
                break

        return full_text[:cut_off_pos], module_start_idx
