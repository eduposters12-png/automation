import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("listifyai.requests")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - started) * 1000
        logger.info(
            "%s %s %s %.2fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms
        )
        return response


def configure_request_logging(app) -> None:
    logging.basicConfig(level=logging.INFO)
    app.add_middleware(RequestLoggingMiddleware)
