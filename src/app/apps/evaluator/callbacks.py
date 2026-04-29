# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging
from typing import Optional, List
import requests

from django.conf import settings

logger = logging.getLogger(__name__)


def build_unified_payload(status: str, course_key: str, result: any, error: Optional[str] = None, evaluation_id: Optional[str] = None, user_id: Optional[str] = None) -> dict:
    """Build the standard response payload used by all callbacks."""

    payload = {
        "status": status,
        "result": result if result is not None else {},
        "course_key": course_key,
    }

    if evaluation_id:
        payload["evaluation_id"] = evaluation_id
    if user_id:
        payload["user_id"] = user_id
    if error:
        payload["error"] = error

    return payload


def send_snapshot_callback(callback_url: str, snapshot_text: str, course_key: str, evaluation_id: Optional[str], qip_user_id: Optional[str]) -> None:
    """Send a SNAPSHOT_CREATED callback with the generated document digest."""

    payload = build_unified_payload(
        status="SNAPSHOT_CREATED",
        course_key=course_key,
        result=snapshot_text,
        evaluation_id=evaluation_id,
        user_id=qip_user_id,
    )
    headers = {
        "Content-Type": "application/json",
        "X-Callback-Secret": settings.QIP_CALLBACK_SECRET,
    }

    try:
        requests.post(callback_url, json=payload, headers=headers, timeout=60)
        logger.info(f"[{evaluation_id}] Snapshot callback sent.")
    except Exception as e:
        logger.warning(f"[{evaluation_id}] Failed to send snapshot callback: {e}")


def send_interim_callback(callback_url: str, interim_json: dict, course_key: str, evaluation_id: Optional[str], qip_user_id: Optional[str]) -> None:
    """Send a CRITERION_COMPLETE callback after each criterion is evaluated."""

    payload = build_unified_payload(
        status="CRITERION_COMPLETE",
        course_key=course_key,
        result=interim_json,
        evaluation_id=evaluation_id,
        user_id=qip_user_id,
    )
    headers = {
        "Content-Type": "application/json",
        "X-Callback-Secret": settings.QIP_CALLBACK_SECRET,
    }

    try:
        requests.post(callback_url, json=payload, headers=headers, timeout=60)
        logger.info(f"[{evaluation_id}] Interim callback sent.")
    except requests.exceptions.RequestException as e:
        logger.warning(f"[{evaluation_id}] Failed to send interim callback: {e}")


def send_callback(callback_url: str, course_key: str, status: str, results: Optional[dict], error: Optional[str], evaluation_id: Optional[str], qip_user_id: Optional[str], scan_names: Optional[List[str]] = None) -> None:
    """Send the final COMPLETE or FAILED status callback."""
    
    payload = build_unified_payload(
        status=status,
        course_key=course_key,
        result=results,
        error=error,
        evaluation_id=evaluation_id,
        user_id=qip_user_id,
    )

    if scan_names:
        payload["scan_names"] = scan_names

    headers = {
        "Content-Type": "application/json",
        "X-Callback-Secret": settings.QIP_CALLBACK_SECRET,
    }

    try:
        response = requests.post(callback_url, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        logger.info(f"[{evaluation_id}] Final callback sent to {callback_url}.")
    except requests.exceptions.RequestException as e:
        logger.error(f"[{evaluation_id}] Failed to send final callback to {callback_url}: {e}")
