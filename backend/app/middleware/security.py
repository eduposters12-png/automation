from urllib.parse import urlparse

from starlette.middleware.trustedhost import TrustedHostMiddleware

from backend.app.core.config import get_settings


def _hostname(value: object) -> str | None:
    parsed = urlparse(str(value))
    return parsed.hostname


def configure_security_middleware(app) -> None:
    settings = get_settings()
    allowed_hosts = {
        "localhost",
        "127.0.0.1",
        "testserver",
        _hostname(settings.frontend_url),
        _hostname(settings.backend_url)
    }
    if settings.cookie_domain:
        allowed_hosts.add(settings.cookie_domain.lstrip("."))
        allowed_hosts.add(f"*.{settings.cookie_domain.lstrip('.')}")
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=[host for host in allowed_hosts if host])
