# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import concurrent.futures
import logging
from typing import List
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .cleaning import clean_text_block
from .client import LEARNIFY_BASE_URL, LearnifyClient
from .parser import extract_text_from_content
from .sections import select_module_section

logger = logging.getLogger(__name__)

CONTENT_BASE_URL = f"{LEARNIFY_BASE_URL}/page"


def get_clean_content(page_tree: list) -> List[dict]:
    """
    Fetch all pageType=9 page contents in parallel and flag the metadata anchor — the
    FIRST content page of the chosen section (named Module/Chapter, else the first non-empty
    section, else the first content page in the tree). Only that one page is flagged, so
    metadata extraction targets it instead of sweeping the whole section.
    """

    # 1. Collect IDs first. `is_first` marks the single metadata anchor page.
    section = select_module_section(page_tree)
    section_id = section.get("id") if section else None

    target_ids = []
    anchored = [False]

    def collect(pages, inside_metadata):
        for p in pages:
            page_type = p.get("pageType")
            children = p.get("pages") or []
            is_chosen_section = page_type == 8 and p.get("id") == section_id

            if is_chosen_section:
                # Keep the section container itself (its intro text) in the corpus.
                target_ids.append({"id": p["id"], "is_first": False, "title": p.get("title", "")})

            if page_type == 9:
                is_first = inside_metadata and not anchored[0]
                if is_first:
                    anchored[0] = True
                target_ids.append({"id": p["id"], "is_first": is_first, "title": p.get("title", "")})
            elif children:
                collect(children, inside_metadata or is_chosen_section)

    # With no qualifying section, treat the whole tree as eligible so the first
    # content page overall becomes the metadata anchor.
    collect(page_tree, inside_metadata=section is None)

    logger.info(f"Downloading {len(target_ids)} pages in PARALLEL")

    # 2. Worker function
    def fetch_one(target, session):
        pid = target["id"]
        try:
            r = session.get(f"{CONTENT_BASE_URL}/{pid}/content", timeout=15)
            if r.ok:
                data = extract_text_from_content(r.json())
                data["is_first_module_section"] = target["is_first"]
                return data
            elif target["is_first"]:
                return {
                    "id": pid,
                    "title": clean_text_block(target.get("title", "")),
                    "videos": [],
                    "sections": [],
                    "is_first_module_section": True,
                }
            else:
                logger.warning(f"Failed to fetch content for page {pid}: {r.status_code}")
        except Exception as e:
            logger.error(f"Error fetching page {pid}: {e}")
        return None

    # 3. Execute Pool
    results = []
    with requests.Session() as session:
        adapter = HTTPAdapter(pool_connections=10, pool_maxsize=10, max_retries=Retry(total=3, backoff_factor=0.5))
        session.mount("https://", adapter)

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(lambda t: fetch_one(t, session), target_ids))

    return [r for r in results if r]


def fetch_module_content(course_key: str) -> List[dict]:
    """Fetch all module content from the Learnify API for the given course_key."""

    logger.info(f"Fetching course structure for key: {course_key}")
    with LearnifyClient() as client:
        root_data = client.get_page_structure(course_key)

    if not root_data:
        raise Exception(f"Failed to load structure for course key: {course_key}")

    pages = root_data.get("pages", [])
    cleaned = get_clean_content(pages)
    root_title = root_data.get("title")
    if isinstance(root_title, dict):
        root_title = root_title.get("en") or next(iter(root_title.values()), "")
    if isinstance(root_title, str) and root_title.strip():
        cleaned.insert(0, {
            "id": root_data.get("id"),
            "title": clean_text_block(root_title),
            "videos": [],
            "sections": [],
        })

    logger.info(f"Extracted {len(cleaned)} content pages (pageType=9)")
    return cleaned
