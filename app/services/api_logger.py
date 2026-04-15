import json

from app.models.api_log import ApiLog, LogDirection
from app.services.sanitizer import PiiSanitizer

sanitizer = PiiSanitizer()

SENSITIVE_HEADERS = {"authorization", "digital-signature", "cookie", "set-cookie"}


def _sanitize_headers(headers):
    return {
        k: "***" if k.lower() in SENSITIVE_HEADERS else v
        for k, v in headers.items()
    }


def _parse_body(raw):
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="replace")
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return {"_raw": raw}
    return {}


def log_incoming(method, url, headers, body, status_code=None):
    parsed_body = _parse_body(body)
    return ApiLog.create(
        direction=LogDirection.INCOMING.value,
        method=method,
        url=url,
        status_code=status_code,
        headers=_sanitize_headers(dict(headers)),
        body=sanitizer.sanitize(parsed_body),
    )


def log_outgoing(method, url, headers, body, status_code=None):
    parsed_body = _parse_body(body)
    return ApiLog.create(
        direction=LogDirection.OUTGOING.value,
        method=method,
        url=url,
        status_code=status_code,
        headers=_sanitize_headers(dict(headers) if headers else {}),
        body=sanitizer.sanitize(parsed_body),
    )
