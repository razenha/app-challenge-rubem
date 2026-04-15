import json
import logging
import time

from flask import g, request

from app.services.sanitizer import PiiSanitizer

logger = logging.getLogger("request")
sanitizer = PiiSanitizer()


def _parse_body():
    if not request.data:
        return {}
    try:
        return json.loads(request.data.decode("utf-8"))
    except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
        return {"_raw": request.data[:200].decode("utf-8", errors="replace")}


def _format_dict(data):
    if not data:
        return "{}"
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def init_request_logger(app):
    @app.before_request
    def _start_timer():
        g.request_start_time = time.monotonic()

    @app.after_request
    def _log_request(response):
        duration_ms = int((time.monotonic() - g.request_start_time) * 1000)

        params = sanitizer.sanitize(request.args.to_dict(flat=True))
        body = sanitizer.sanitize(_parse_body())

        logger.info(
            "method=%s path=%s status=%d duration_ms=%d params=%s body=%s",
            request.method,
            request.path,
            response.status_code,
            duration_ms,
            _format_dict(params),
            _format_dict(body),
        )

        return response
