"""
backend/app/middleware/logging_middleware.py
─────────────────────────────────────────────
Structured request/response logging with structlog.
Register as a Flask before/after request handler.
"""

import time
import structlog
from flask import request, g

logger = structlog.get_logger()


def register_logging(app):
    """Attach logging hooks to a Flask app."""

    @app.before_request
    def _start_timer():
        g.start_time = time.perf_counter()

    @app.after_request
    def _log_request(response):
        duration_ms = round((time.perf_counter() - g.start_time) * 1000, 2)
        logger.info(
            "request",
            method=request.method,
            path=request.path,
            status=response.status_code,
            duration_ms=duration_ms,
            ip=request.remote_addr,
        )
        return response
