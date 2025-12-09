"""Pydantic models for API request/response."""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    """Chat request payload."""

    message: str
    session_id: str | None = None
