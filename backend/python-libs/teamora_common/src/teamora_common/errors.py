"""The one JSON error shape every Teamora API returns: ``{ reason, message, details? }`` (Readiness doc §2.3)."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("teamora.errors")

REASON_BY_STATUS = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_failed",
    429: "too_many_requests",
}


class ApiError(Exception):
    """An error response with an explicit status and body.

    ``body`` normally is ``{reason, message, details?}``; a few endpoints add documented extra keys
    (e.g. ``current_matrix_revision`` on a 409 revision_mismatch, TDD §8).
    """

    def __init__(self, status_code: int, reason: str, message: str, details: Any = None, **extra: Any) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body: dict[str, Any] = {"reason": reason, "message": message}
        if details is not None:
            self.body["details"] = details
        self.body.update(extra)


def unprocessable(details: list[dict[str, str]]) -> ApiError:
    return ApiError(422, "validation_failed", "The request body is invalid.", details)


#: Friendlier "is required" wording for fields where a missing value has a specific meaning.
MISSING_FIELD_HINTS: dict[str, str] = {}

_PROBLEM_BY_TYPE = {
    "missing": "is required",
    "string_type": "must be a string",
    "int_type": "must be an integer",
    "int_parsing": "must be an integer",
    "float_type": "must be a number",
    "bool_type": "must be true or false",
    "list_type": "must be an array",
    "dict_type": "must be a JSON object",
    "model_type": "must be a JSON object",
    "model_attributes_type": "must be a JSON object",
    "json_invalid": "must be valid JSON",
}


def _field_name(loc: tuple[Any, ...]) -> str:
    parts = list(loc[1:]) if loc and loc[0] in ("body", "query", "path") else list(loc)
    name = ""
    for part in parts:
        name += f"[{part}]" if isinstance(part, int) else (f".{part}" if name else str(part))
    return name or "(body)"


def _problem(error: dict[str, Any], field: str) -> str:
    kind = error.get("type", "")
    if kind == "missing" and field in MISSING_FIELD_HINTS:
        return MISSING_FIELD_HINTS[field]
    if kind == "value_error":
        return str(error.get("ctx", {}).get("error", error.get("msg", "is invalid")))
    if kind == "literal_error":
        return f"must be {error.get('ctx', {}).get('expected', 'one of the allowed values')}"
    return _PROBLEM_BY_TYPE.get(kind, str(error.get("msg", "is invalid")))


def validation_details(exc: RequestValidationError) -> list[dict[str, str]]:
    details: list[dict[str, str]] = []
    for error in exc.errors():
        field = _field_name(tuple(error.get("loc", ())))
        details.append({"field": field, "problem": _problem(error, field)})
    return details


def install_error_handlers(app: FastAPI) -> None:
    """Normalises every error into ``{reason, message, details?}``; unexpected errors become a bare 500."""

    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(exc.body, status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(unprocessable(validation_details(exc)).body, status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        body = {"reason": REASON_BY_STATUS.get(exc.status_code, "error"), "message": str(exc.detail)}
        return JSONResponse(body, status_code=exc.status_code, headers=getattr(exc, "headers", None))

    @app.exception_handler(Exception)
    async def _unexpected(_: Request, exc: Exception) -> JSONResponse:
        # No internals in the response; the stack trace goes to the log instead.
        logger.exception("unhandled error", exc_info=exc)
        return JSONResponse({"reason": "internal_error", "message": "Internal server error"}, status_code=500)
