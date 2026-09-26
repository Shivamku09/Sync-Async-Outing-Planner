from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.common.exceptions import AsyncBacklogExceededError, InvalidCallbackURLError, RequestNotFoundError


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def invalid_request(_: Request, exc: RequestValidationError) -> JSONResponse:
        error = exc.errors()[0] if exc.errors() else {}
        field = ".".join(str(part) for part in error.get("loc", []) if part != "body")
        reason = str(error.get("msg", "invalid value"))
        message = f"{field}: {reason}" if field else reason
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "INVALID_REQUEST", "message": message, "request_id": None}},
        )

    @app.exception_handler(RequestNotFoundError)
    async def request_not_found(_: Request, exc: RequestNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"error": {"code": exc.code, "message": "request not found", "request_id": None}})

    @app.exception_handler(InvalidCallbackURLError)
    async def invalid_callback(_: Request, exc: InvalidCallbackURLError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"error": {"code": exc.code, "message": "callback_url is not allowed", "request_id": None}})

    @app.exception_handler(AsyncBacklogExceededError)
    async def backlog_exceeded(_: Request, exc: AsyncBacklogExceededError) -> JSONResponse:
        return JSONResponse(
            status_code=429, headers={"Retry-After": "1"},
            content={"error": {"code": exc.code, "message": "async backlog limit reached", "request_id": None}},
        )
