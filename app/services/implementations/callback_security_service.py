import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit

from app.common.exceptions import InvalidCallbackURLError
from app.services.interfaces.callback_security_service import CallbackSecurityService


class DefaultCallbackSecurityService(CallbackSecurityService):
    def __init__(self, allow_localhost: bool, allowed_hosts: list[str] | None = None) -> None:
        self._allow_localhost = allow_localhost
        self._allowed_hosts = {host.lower() for host in (allowed_hosts or [])}

    async def validate_destination(self, url: str) -> None:
        parsed = urlsplit(url)
        if parsed.username or parsed.password or not parsed.hostname:
            raise InvalidCallbackURLError()
        hostname = parsed.hostname.lower()
        explicitly_allowed = hostname in self._allowed_hosts
        if parsed.scheme != "https" and not ((self._allow_localhost or explicitly_allowed) and parsed.scheme == "http"):
            raise InvalidCallbackURLError()
        if explicitly_allowed:
            return
        if parsed.port and parsed.port not in ({80, 443} if self._allow_localhost else {443}):
            raise InvalidCallbackURLError()

        if self._allow_localhost and hostname in {"localhost", "127.0.0.1", "::1"}:
            return
        try:
            addresses = await asyncio.get_running_loop().run_in_executor(
                None, lambda: socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
            )
        except socket.gaierror as exc:
            raise InvalidCallbackURLError() from exc
        for item in addresses:
            address = ipaddress.ip_address(item[4][0])
            if not address.is_global:
                raise InvalidCallbackURLError()
