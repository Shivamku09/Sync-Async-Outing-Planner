from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import httpx

from app.config.settings import CallbackSettings


@dataclass(frozen=True, slots=True)
class HTTPResult:
    status_code: int
    body: bytes


class HTTPAPIClient(ABC):
    @abstractmethod
    async def post(self, url: str, payload: dict[str, Any], headers: dict[str, str]) -> HTTPResult: ...

    @abstractmethod
    async def close(self) -> None: ...


class HttpxAPIClient(HTTPAPIClient):
    def __init__(self, settings: CallbackSettings) -> None:
        timeout = httpx.Timeout(settings.read_timeout_seconds, connect=settings.connect_timeout_seconds)
        self._max_response_bytes = settings.max_response_bytes
        self._client = httpx.AsyncClient(timeout=timeout, follow_redirects=False)

    async def post(self, url: str, payload: dict[str, Any], headers: dict[str, str]) -> HTTPResult:
        async with self._client.stream("POST", url, json=payload, headers=headers) as response:
            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > self._max_response_bytes:
                    raise ValueError("callback response exceeded configured size")
            return HTTPResult(response.status_code, bytes(body))

    async def close(self) -> None:
        await self._client.aclose()
