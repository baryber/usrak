from starlette.types import ASGIApp, Receive, Scope, Send


class TrustedHostMiddleware:
    def __init__(self, app: ASGIApp, trusted_proxies: list[str]):
        self.app = app
        self.trusted_proxies = trusted_proxies

    def is_trusted_proxy(self, ip: str) -> bool:
        return ip in self.trusted_proxies

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        client_host = scope.get("client")
        if client_host:
            ip, _ = client_host
            if not self.is_trusted_proxy(ip):
                print(f"Untrusted proxy: {ip}")

        await self.app(scope, receive, send)
