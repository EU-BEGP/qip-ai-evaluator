# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging
from typing import Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

LEARNIFY_BASE_URL = "https://time.learnify.se/learnifyer/api/2"
LEARNIFY_TIMEOUT = 10


class LearnifyUnavailableError(Exception):
    """Raised when the Learnify service cannot be reached (connection/timeout)."""


class LearnifyClient:
    """Fail-fast HTTP client for the Learnify API. No retries, short timeout."""

    def __init__(self, max_workers: int = 20):
        self._session = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=max_workers,
            pool_maxsize=max_workers,
            max_retries=Retry(total=0),
        )
        self._session.mount("https://", adapter)

    def get_page_structure(self, course_key: str) -> Optional[dict]:
        """
        Fetches the root page structure for a course.
        Returns None on HTTP errors (module-level issue), raises LearnifyUnavailableError when Learnify is unreachable.
        """

        url = f"{LEARNIFY_BASE_URL}/page/0?key={course_key}"
        try:
            response = self._session.get(url, timeout=LEARNIFY_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"Learnify HTTP {e.response.status_code} for '{course_key}'")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Learnify unreachable for '{course_key}': {e}")
            raise LearnifyUnavailableError(str(e)) from e

    def close(self):
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def fetch_module_last_modified(course_key: str, client: Optional[LearnifyClient] = None) -> Optional[str]:
    """Return a module's latest modification date from the Learnify API"""

    logger.info(f"Fetching module modified date for key: {course_key}")
    owns_client = client is None
    client = client or LearnifyClient()

    try:
        root_data = client.get_page_structure(course_key)
        if not root_data:
            return None

        dates = []

        def collect_modified(node):
            if node.get("modified"):
                dates.append(node["modified"])
            for child in node.get("pages", []):
                collect_modified(child)

        collect_modified(root_data)

        return max(dates) if dates else None
    finally:
        if owns_client:
            client.close()
