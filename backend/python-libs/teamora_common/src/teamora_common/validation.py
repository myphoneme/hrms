"""Reusable request-field types for Pydantic models.

Each type does its whole check in one validator, so a bad value produces exactly one
``{field, problem}`` entry in a 422 response (see errors.py), worded the same in every service.
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import PlainValidator, WithJsonSchema

from .db import is_uuid


def _uuid(value: Any) -> str:
    if not is_uuid(value):
        raise ValueError("must be a UUID")
    # Lowercase, as PostgreSQL returns them, so ids from requests and rows compare equal.
    return value.lower()


Uuid = Annotated[str, PlainValidator(_uuid), WithJsonSchema({"type": "string", "format": "uuid"})]


def text(max_length: int) -> Any:
    """A non-empty string of at most ``max_length`` characters (whitespace-only counts as empty)."""

    def check(value: Any) -> str:
        if not isinstance(value, str) or value.strip() == "":
            raise ValueError("must be a non-empty string")
        if len(value) > max_length:
            raise ValueError(f"must be at most {max_length} characters")
        return value

    return Annotated[str, PlainValidator(check), WithJsonSchema({"type": "string", "minLength": 1, "maxLength": max_length})]


def _positive_int(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("must be a positive integer")
    return value


PositiveInt = Annotated[int, PlainValidator(_positive_int), WithJsonSchema({"type": "integer", "minimum": 1})]
