"""Error handling utilities for LLM streaming."""

from dataclasses import dataclass
from enum import Enum


class ErrorCategory(Enum):
    """Categories of errors for handling strategy."""

    RATE_LIMIT = "rate_limit"
    TOKEN_LIMIT = "token_limit"
    EMPTY_STREAM = "empty_stream"
    NETWORK = "network"
    AUTH = "auth"
    UNKNOWN = "unknown"


@dataclass
class LLMError:
    """Structured LLM error."""

    category: ErrorCategory
    message: str
    original_error: Exception | None = None
    retryable: bool = True

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "category": self.category.value,
            "message": self.message,
            "retryable": self.retryable,
        }


def classify_error(error: Exception) -> LLMError:
    """Classify an exception into an LLMError.

    Handles errors from Azure OpenAI, Anthropic Claude, Google Gemini.
    """
    error_str = str(error).lower()

    # Rate limit errors (common across providers)
    if any(
        x in error_str for x in ["rate limit", "429", "too many requests", "quota"]
    ):
        return LLMError(
            category=ErrorCategory.RATE_LIMIT,
            message="API 速率限制，稍後重試...",
            original_error=error,
            retryable=True,
        )

    # Token limit errors
    if any(x in error_str for x in ["token", "context length", "max_tokens"]):
        return LLMError(
            category=ErrorCategory.TOKEN_LIMIT,
            message="訊息過長，請開啟新對話。",
            original_error=error,
            retryable=False,
        )

    # Empty stream (the specific error we're targeting)
    if "no generations found in stream" in error_str:
        return LLMError(
            category=ErrorCategory.EMPTY_STREAM,
            message="LLM 回傳空結果，重試中...",
            original_error=error,
            retryable=True,
        )

    # Network errors
    if any(x in error_str for x in ["connection", "timeout", "network", "ssl"]):
        return LLMError(
            category=ErrorCategory.NETWORK,
            message="連線問題，重試中...",
            original_error=error,
            retryable=True,
        )

    # Auth errors
    if any(x in error_str for x in ["api key", "unauthorized", "401", "403"]):
        return LLMError(
            category=ErrorCategory.AUTH,
            message="API 認證失敗，請檢查設定。",
            original_error=error,
            retryable=False,
        )

    return LLMError(
        category=ErrorCategory.UNKNOWN,
        message=f"發生錯誤: {str(error)[:100]}",
        original_error=error,
        retryable=False,
    )
