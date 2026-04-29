# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging
import requests
import datetime
from dateutil.parser import isoparse

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class RagService:
    """Handles external RAG API communication."""

    CACHE_TIMEOUT = 300
    CACHE_TIMEOUT_FAIL = 100
    
    @staticmethod
    def clean_title(title):
        """Cleans the title by removing leading and trailing whitespaces and quotes."""
        
        if not title:
            return "Untitled Module"
        return str(title).strip().strip('"').strip("'").lstrip('#').strip()
    
    @staticmethod
    def _cache_key(course_key):
        return f"rag:last_modified:{course_key}"
    
    @staticmethod
    def invalidate_cache(course_key):
        """Deletes the cache entry for the given course key."""
        
        key = RagService._cache_key(course_key)
        cache.delete(key)

    @classmethod
    def get_last_modified(cls, course_key, force=False):
        """Single fetch using bulk logic (unified approach)."""

        result = cls.get_bulk_last_modified([course_key], force=force)
        return result.get(course_key)
    
    @staticmethod
    def is_outdated(rag_date, evaluated_at):
        """
        Safely compares the RAG last modified date with the local evaluation date.
        Normalizes both to UTC aware datetimes and ignores seconds to prevent false positives.
        """

        if not rag_date or not evaluated_at:
            return False

        try:
            from django.utils import timezone
            
            safe_rag_date = rag_date
            if isinstance(safe_rag_date, str):
                from dateutil.parser import isoparse
                safe_rag_date = isoparse(safe_rag_date)
                
            if timezone.is_naive(safe_rag_date):
                safe_rag_date = timezone.make_aware(safe_rag_date, timezone.utc)
                
            safe_eval_date = evaluated_at
            if timezone.is_naive(safe_eval_date):
                safe_eval_date = timezone.make_aware(safe_eval_date, timezone.utc)

            return safe_rag_date.replace(second=0, microsecond=0) > safe_eval_date.replace(second=0, microsecond=0)
            
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Date comparison error: {e}")
            return False

    @classmethod
    def get_bulk_last_modified(cls, course_keys, force=False):
        """Return last_modified datetimes for a list of course keys."""

        result = {}
        missing_keys = []

        if not force:
            # Cache lookup
            for key in course_keys:
                cached = cache.get(cls._cache_key(key))
                if cached is not None:
                    result[key] = cached
                else:
                    missing_keys.append(key)
        else:
            missing_keys = list(course_keys)

        # Fetch missing (or all when forced)
        if missing_keys:
            fetched = cls._fetch_bulk(missing_keys)

            for key in missing_keys:
                value = fetched.get(key)

                timeout = cls.CACHE_TIMEOUT if value else cls.CACHE_TIMEOUT_FAIL
                cache.set(cls._cache_key(key), value, timeout)

                result[key] = value

        return result

    @classmethod
    def _fetch_bulk(cls, course_keys):
        try:
            logger.info(f"Requesting bulk last_modified for {len(course_keys)} modules")

            response = requests.post(settings.RAG_API_MODULE_MODIFIED_URL,json={"course_keys": course_keys},timeout=100)
            response.raise_for_status()
            data = response.json().get("results", {})
            parsed = {}

            for key in course_keys:
                value = data.get(key)

                if value:
                    dt = isoparse(value)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=datetime.timezone.utc)
                    parsed[key] = dt
                else:
                    parsed[key] = None

            return parsed

        except Exception as e:
            logger.error(f"Bulk RAG Error: {str(e)}")
            return {key: None for key in course_keys}

    @staticmethod
    def trigger_evaluation(payload):
        """Dispatches the evaluation task to the external RAG system."""
        
        evaluation_id = payload.get('evaluation_id')
        logger.info(f"Dispatching evaluation task to RAG API for evaluation ID {evaluation_id}")
        try:
            response = requests.post(settings.RAG_API_EVALUATE_URL, json=payload, timeout=200)
            response.raise_for_status()
            return response.status_code
        except requests.exceptions.RequestException as e:
            logger.error(f"RAG API Error while triggering evaluation ID {evaluation_id}: {str(e)}")
            raise e
        
    @staticmethod
    def fetch_metadata(course_key):
        """Retrieves module metadata from the external RAG API."""
        
        logger.info("Requesting metadata from RAG API")
        try:
            url = getattr(settings, 'RAG_API_METADATA_URL', None)
            if not url:
                logger.error("RAG_API_METADATA_URL is not configured")
                return None
            
            response = requests.post(url, json={'course_key': course_key}, timeout=300)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"RAG API Error during metadata fetch: {str(e)}")
            return None
