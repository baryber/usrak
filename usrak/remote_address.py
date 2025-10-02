from starlette.requests import Request
from starlette.requests import HTTPConnection

from usrak.core.dependencies.config_provider import get_app_config


def get_remote_address(request: Request | HTTPConnection) -> str:
    client_host = request.client.host if request.client else "unknown"

    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if not x_forwarded_for:
        return client_host

    forwarded_ips = [ip.strip() for ip in x_forwarded_for.split(",")]

    if len(forwarded_ips) == 0:
        return client_host

    immediate_client_ip = client_host

    config = get_app_config()
    trusted_proxies = config.TRUSTED_PROXIES

    if immediate_client_ip not in trusted_proxies:
        return immediate_client_ip

    for ip in reversed(forwarded_ips):
        if ip and ip not in trusted_proxies:
            return ip

    return forwarded_ips[0] if forwarded_ips else client_host
