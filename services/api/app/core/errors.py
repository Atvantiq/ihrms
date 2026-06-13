"""Global exception handling — consistent envelope, no stack-trace leaks.

All errors return {"detail": ..., "request_id": ...}. Expected errors
(HTTPException, validation) keep their status and message; unexpected errors
are logged server-side with the full traceback and return a generic 500 so
internals never reach the client.
"""

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.observability import log, request_id_ctx


def _envelope(detail: Any, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail, "request_id": request_id_ctx.get()},
        headers={"X-Request-ID": request_id_ctx.get()},
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exc(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _envelope(exc.detail, exc.status_code)

    @app.exception_handler(HTTPException)
    async def fastapi_http_exc(_: Request, exc: HTTPException) -> JSONResponse:
        return _envelope(exc.detail, exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_exc(_: Request, exc: RequestValidationError) -> JSONResponse:
        return _envelope(exc.errors(), 422)

    @app.exception_handler(Exception)
    async def unhandled_exc(request: Request, exc: Exception) -> JSONResponse:
        log.exception(
            "unhandled_error",
            extra={"extra_fields": {"path": request.url.path, "error": str(exc)}},
        )
        return _envelope("Internal server error", 500)
