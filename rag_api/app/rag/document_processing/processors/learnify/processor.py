# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging
from typing import Dict, List
from langchain_core.documents import Document

from ...core import DocumentLoader
from .fetcher import fetch_module_content

logger = logging.getLogger(__name__)


class LearnifyProcessor(DocumentLoader):
    """Processes content from Learnify API and converts to Document objects."""

    def __init__(self):
        pass

    def convert_to_documents(self, module_data: List[Dict]) -> List[Document]:
        """Convert module data to LangChain Document objects — one Document per page."""

        documents = []
        course_title = module_data[0].get("title", "") if module_data else ""
        total_pages = len(module_data)

        for i, page in enumerate(module_data, 1):
            page_title = page.get("title", "")
            page_id = page.get("id")
            is_first = page.get("is_first_module_section", False)

            content_parts = []
            if page_title:
                content_parts.append(f"# {page_title}")
            for vid in page.get("videos", []):
                content_parts.append(f"Video: {vid}")
            for sec in page.get("sections", []):
                if "subtitle" in sec:
                    if sec.get("subtitle"):
                        content_parts.append(f"## {sec['subtitle']}")
                    if sec.get("text"):
                        content_parts.append(sec["text"])
                elif "question" in sec:
                    content_parts.append(f"**Q: {sec['question']}**")
                    for ans in sec.get("answers", []):
                        content_parts.append(f"- {ans}")

            if content_parts:
                documents.append(Document(
                    page_content="\n\n".join(content_parts),
                    metadata={
                        "source": f"learnify_module_page_{i}",
                        "page_id": page_id,
                        "page_title": page_title,
                        "title": page_title,
                        "page_number": i,
                        "total_pages": total_pages,
                        "source_type": "learnify_api",
                        "is_first_module_section": is_first,
                        "heading_path": " > ".join(filter(None, [course_title, page_title])),
                    }
                ))

        return documents

    def load_document(self, course_key: str) -> List[Document]:
        """
        Load document from Learnify API using course key.
        Args:
            course_key: The course key for the Learnify module (e.g., "OYJPG").
        """

        try:
            module_data = fetch_module_content(course_key)

            if not module_data:
                raise ValueError(f"No content found for course key: {course_key}")

            documents = self.convert_to_documents(module_data)

            if not documents:
                raise ValueError(f"No documents could be created from course key: {course_key}")

            logger.info(f"Successfully loaded {len(documents)} documents from Learnify module {course_key}")
            return documents

        except Exception as e:
            logger.error(f"Failed to load Learnify module {course_key}: {e}")
            raise
