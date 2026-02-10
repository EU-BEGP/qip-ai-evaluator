# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import requests
import re
import logging
import concurrent.futures
from typing import List, Dict
from bs4 import BeautifulSoup
from langchain.schema import Document
from ..document_loader import DocumentLoader
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%H:%M:%S')

class LearnifyProcessor(DocumentLoader):
    """Process content from Learnify API and convert to Document objects"""
    
    def __init__(self):
        self.content_base_url = "https://time.learnify.se/learnifyer/api/2/page"
        self.structure_base_url = "https://time.learnify.se/learnifyer/api/2/page"

    def clean_html(self, html):
        """Convert HTML to readable plain text."""
        if not html:
            return ""
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def clean_text_block(self, text):
        """Normalize whitespace and line breaks."""
        if not text:
            return ""
        text = re.sub(r'\n+', '\n', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def extract_texts_recursively(self, obj, sections, last_value=None, last_question=None):
        """
        Recursively extract and structure text, subtitles, and question-answer groups.
        Returns sections = [{'subtitle': ..., 'text': ...}, {'question': ..., 'answers': [...]}, ...]
        """
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "question" and isinstance(v, str):
                    last_question = self.clean_html(v)

                elif k == "answers" and isinstance(v, list):
                    # Handle structured answers with correctness info
                    for ans in v:
                        if isinstance(ans, dict) and "value" in ans:
                            val = self.clean_html(ans["value"])
                            if ans.get("correct", False):
                                val += " (Correct)"
                            if last_question:
                                if not sections or "question" not in sections[-1] or sections[-1]["question"] != last_question:
                                    sections.append({"question": last_question, "answers": []})
                                sections[-1]["answers"].append(val)

                elif k in ("value",) and isinstance(v, str):
                    val = self.clean_html(v)
                    # If we're inside a question context, append as an answer
                    if last_question:
                        if not sections or "question" not in sections[-1] or sections[-1]["question"] != last_question:
                            sections.append({"question": last_question, "answers": []})
                        sections[-1]["answers"].append(val)
                    # Else treat as subtitle
                    else:
                        last_value = val

                elif k == "body" and isinstance(v, str):
                    text = self.clean_html(v)
                    sections.append({"subtitle": last_value, "text": text})
                    last_value = None
                    last_question = None

                elif isinstance(v, (dict, list)):
                    last_value, last_question = self.extract_texts_recursively(v, sections, last_value, last_question)

        elif isinstance(obj, list):
            for item in obj:
                last_value, last_question = self.extract_texts_recursively(item, sections, last_value, last_question)
        return last_value, last_question

    def extract_text_from_content(self, data):
        """Extract structured sections and Q&A from Learnify content page."""
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

            self.extract_texts_recursively(en, sections)

        # Clean final output
        for s in sections:
            if "subtitle" in s:
                s["subtitle"] = self.clean_text_block(s.get("subtitle", ""))
                s["text"] = self.clean_text_block(s.get("text", ""))
            if "question" in s:
                s["question"] = self.clean_text_block(s.get("question", ""))
                s["answers"] = [self.clean_text_block(a) for a in s.get("answers", [])]

        return {
            "id": contents.get("id"),
            "title": self.clean_text_block(title),
            "videos": video_links,
            "sections": [s for s in sections if any(s.values())]
        }

    def get_clean_content(self, page_tree):
        """Extract content from all pages with pageType=9 using Parallel Retrieval """
        # 1. Collect IDs first
        target_ids = []
        def collect(pages):
            for p in pages:
                if p.get("pageType") == 9:
                    target_ids.append(p["id"])
                elif "pages" in p and p["pages"]:
                    collect(p["pages"])
        collect(page_tree)

        logging.info(f"Downloading {len(target_ids)} pages in PARALLEL")

        # 2. Worker function
        def fetch_one(pid, session):
            try:
                r = session.get(f"{self.content_base_url}/{pid}/content", timeout=15)
                if r.ok:
                    return self.extract_text_from_content(r.json())
                else:
                    logging.warning(f"Failed to fetch content for page {pid}: {r.status_code}")
            except Exception as e:
                logging.error(f"Error fetching page {pid}: {e}")
            return None

        # 3. Execute Pool
        results = []
        with requests.Session() as session:
            # Configure retries
            adapter = HTTPAdapter(pool_connections=10, pool_maxsize=10, max_retries=Retry(total=3, backoff_factor=0.5))
            session.mount("https://", adapter)

            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                # Map maintains order corresponding to target_ids
                results = list(executor.map(lambda pid: fetch_one(pid, session), target_ids))

        return [r for r in results if r]

    def fetch_module_content(self, course_key):
        """Fetch all module content from Learnify API"""
        structure_url = f"{self.structure_base_url}/0?key={course_key}"
        
        logging.info(f"Fetching course structure for key: {course_key}")
        response = requests.get(structure_url)

        if response.ok:
            root_data = response.json()
            pages = root_data.get("pages", [])
            cleaned = self.get_clean_content(pages)
            root_title = root_data.get("title")
            if isinstance(root_title, dict):
                root_title = root_title.get("en") or next(iter(root_title.values()), "")
            if isinstance(root_title, str) and root_title.strip():
                cleaned.insert(0, {
                    "id": root_data.get("id"),
                    "title": self.clean_text_block(root_title),
                    "videos": [],
                    "sections": []
                })

            logging.info(f"Extracted {len(cleaned)} content pages (pageType=9)")
            return cleaned
        else:
            error_msg = f"Failed to load structure: {response.status_code}"
            logging.error(error_msg)
            raise Exception(error_msg)

    def convert_to_documents(self, module_data: List[Dict]) -> List[Document]:
        """Convert module data to LangChain Document objects"""
        documents = []
        
        for i, page in enumerate(module_data, 1):
            # Create main content for the page
            content_parts = []
            
            # Add title
            if page.get("title"):
                content_parts.append(f"# {page['title']}")

            # Add videos
            if page.get("videos"):
                for vid in page["videos"]:
                    content_parts.append(f"Video: {vid}")
            
            # Process sections
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
            
            # Create document if we have content
            if content_parts:
                content = "\n\n".join(content_parts)
                doc = Document(
                    page_content=content,
                    metadata={
                        "source": f"learnify_module_page_{i}",
                        "page_id": page.get("id"),
                        "title": page.get("title", ""),
                        "page_number": i,
                        "total_pages": len(module_data),
                        "source_type": "learnify_api"
                    }
                )
                documents.append(doc)
        
        return documents

    def load_document(self, course_key: str) -> List[Document]:
        """
        Load document from Learnify API using course key
        Args:
            course_key: The course key for the Learnify module (e.g., "OYJPG")
        """
        try:
            # Fetch module content
            module_data = self.fetch_module_content(course_key)
            
            if not module_data:
                raise ValueError(f"No content found for course key: {course_key}")
            
            # Convert to documents
            documents = self.convert_to_documents(module_data)
            
            if not documents:
                raise ValueError(f"No documents could be created from course key: {course_key}")
            
            logging.info(f"Successfully loaded {len(documents)} documents from Learnify module {course_key}")
            return documents
            
        except Exception as e:
            logging.error(f"Failed to load Learnify module {course_key}: {e}")
            raise
