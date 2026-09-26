import asyncio
from datetime import UTC, datetime
from time import time
from typing import Any

from fastapi import FastAPI, Header


app = FastAPI(title="Load Test Callback Receiver")
_callbacks: dict[str, dict[str, Any]] = {}
_lock = asyncio.Lock()


@app.get("/healthz")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.post("/callback", status_code=204)
async def receive_callback(
    payload: dict[str, Any],
    x_request_id: str | None = Header(default=None),
) -> None:
    request_id = str(payload.get("id") or x_request_id or "")
    if request_id:
        async with _lock:
            _callbacks[request_id] = {
                "request_id": request_id,
                "received_at_epoch": time(),
                "received_at": datetime.now(UTC).isoformat(),
                "payload": payload,
            }


@app.post("/reset", status_code=204)
async def reset() -> None:
    async with _lock:
        _callbacks.clear()


@app.get("/results")
async def results() -> dict[str, list[dict[str, Any]]]:
    async with _lock:
        return {"items": list(_callbacks.values())}
