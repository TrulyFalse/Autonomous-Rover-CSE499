"""Outbound status reporting to the main server."""
import requests

from .config import MAIN_SERVER_URL


def send_status(state, distance, alignment_locked, initial_assessment_active):
    try:
        requests.post(
            MAIN_SERVER_URL,
            json={
                'state': state,
                'distance': distance,
                'alignment_locked': alignment_locked,
                'initial_assessment_active': initial_assessment_active,
            },
            timeout=0.5,
        )
    except requests.exceptions.RequestException:
        pass
