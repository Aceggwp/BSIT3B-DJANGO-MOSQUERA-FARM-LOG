"""Shared HTTP error formatting for the AI backends.

Gemini and OpenRouter return useful messages in the body of 4xx/5xx responses
(e.g. "API key not valid"). urllib's default HTTPError string only contains
"HTTP Error 400: Bad Request", so extract the body for a diagnosable message.
"""

import json
import urllib.error


def http_error_message(label: str, exc: urllib.error.HTTPError) -> str:
    detail = ""
    try:
        detail = exc.read().decode("utf-8", "replace").strip()
    except Exception:
        pass

    if detail:
        try:
            payload = json.loads(detail)
            error = payload.get("error") if isinstance(payload, dict) else None
            detail = error.get("message") if isinstance(error, dict) else error or detail
        except (ValueError, AttributeError):
            pass

    detail = str(detail)[:300]
    return f"{label} request failed (HTTP {exc.code}): {detail or exc.reason}"
