"""
Research Agent — Logging Middleware

Provides structured JSON logging and request/response tracing.
Every request is logged with timing, status, and trace ID.
"""

import logging
import time
import uuid
import sys
from pythonjsonlogger import json as json_logger


class RequestLoggingMiddleware:
    """WSGI middleware that logs every request with timing and trace ID."""

    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger('request')

    def __call__(self, environ, start_response):
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        method = environ.get('REQUEST_METHOD', '')
        path = environ.get('PATH_INFO', '')

        # Capture the response status
        response_status = [None]

        def custom_start_response(status, headers, exc_info=None):
            response_status[0] = status
            # Add request ID to response headers
            headers.append(('X-Request-ID', request_id))
            return start_response(status, headers, exc_info)

        try:
            response = self.app(environ, custom_start_response)
            return response
        finally:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            status_code = response_status[0].split(' ')[0] if response_status[0] else '500'

            self.logger.info(
                "request_completed",
                extra={
                    'request_id': request_id,
                    'method': method,
                    'path': path,
                    'status': status_code,
                    'duration_ms': duration_ms
                }
            )


def setup_logging(app):
    """
    Configure structured JSON logging for the application.
    
    In development, uses a readable format.
    In production, uses JSON for log aggregation.
    """
    log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO').upper())

    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    if app.config.get('DEBUG'):
        # Development: readable colored output
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
            datefmt='%H:%M:%S'
        )
    else:
        # Production: JSON structured logging
        formatter = json_logger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s',
            timestamp=True
        )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.setLevel(log_level)

    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Suppress noisy loggers
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('chromadb').setLevel(logging.WARNING)
    logging.getLogger('sentence_transformers').setLevel(logging.WARNING)
    logging.getLogger('transformers').setLevel(logging.WARNING)
    logging.getLogger('huggingface_hub').setLevel(logging.WARNING)
