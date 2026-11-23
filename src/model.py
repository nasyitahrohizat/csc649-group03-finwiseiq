"""Backend OpenAI API client and context-based answer generation for FinWiseIQ."""

import logging
import os
from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    OpenAI,
    OpenAIError,
    RateLimitError,
)

from src.prompt import SYSTEM_PROMPT

load_dotenv()

logger = logging.getLogger(__name__)


class GenerationError(Exception):
    """Raised when OpenAI answer generation fails or returns an invalid response."""


def _sanitize_error_text(text: str) -> str:
    """Redact API keys or sensitive tokens before logging."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    sanitized = str(text)
    if api_key:
        sanitized = sanitized.replace(api_key, "[REDACTED]")
    return sanitized


def get_openai_client() -> OpenAI:
    """Return an authenticated OpenAI client using environment variables."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your_openai_api_key_here":
        raise GenerationError(
            "The AI service is currently unavailable due to a configuration issue."
        )
    return OpenAI(api_key=api_key, timeout=30)


def get_model_name() -> str:
    """Return the configured OpenAI model ID from environment variables."""
    model = os.getenv("OPENAI_MODEL", "").strip()
    if not model:
        raise GenerationError(
            "The AI service is currently unavailable due to a configuration issue."
        )
    return model


def generate_answer(question: str, context: str) -> str:
    """Generate a grounded educational answer using retrieved context and OpenAI API.

    Args:
        question: The user's question string.
        context: Numbered top-3 retrieved Q&A passages from the knowledge base.

    Returns:
        Clean generated answer text grounded in the supplied context.

    Raises:
        ValueError: If question or context is missing or empty.
        GenerationError: If the OpenAI API call fails or returns an invalid response,
            carrying a safe, user-friendly message without leaking internal details.
    """
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Question must be a non-empty string.")

    if not isinstance(context, str) or not context.strip():
        raise ValueError("Context must be a non-empty string.")

    user_prompt = f"CONTEXT:\n{context.strip()}\n\nUSER QUESTION:\n{question.strip()}"

    try:
        client = get_openai_client()
        model = get_model_name()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
    except GenerationError:
        raise
    except APITimeoutError as exc:
        logger.warning("OpenAI request timed out: %s", _sanitize_error_text(str(exc)))
        raise GenerationError(
            "The AI service took too long to respond. Please try again in a moment."
        ) from None
    except AuthenticationError as exc:
        logger.error("OpenAI authentication failed: %s", _sanitize_error_text(str(exc)))
        raise GenerationError(
            "The AI service is currently unavailable due to an authentication issue."
        ) from None
    except RateLimitError as exc:
        logger.warning("OpenAI rate limit reached: %s", _sanitize_error_text(str(exc)))
        raise GenerationError(
            "The AI service is currently busy. Please wait a moment and try again."
        ) from None
    except (NotFoundError, BadRequestError) as exc:
        logger.error("OpenAI model or request error: %s", _sanitize_error_text(str(exc)))
        raise GenerationError(
            "The requested AI model is currently unavailable. Please try again later."
        ) from None
    except APIConnectionError as exc:
        logger.error("OpenAI connection error: %s", _sanitize_error_text(str(exc)))
        raise GenerationError(
            "Unable to connect to the AI service. Please check your connection and try again."
        ) from None
    except OpenAIError as exc:
        logger.error("OpenAI API error: %s", _sanitize_error_text(str(exc)))
        raise GenerationError(
            "The AI service encountered an unexpected error. Please try again later."
        ) from None
    except Exception as exc:
        logger.error("Unexpected generation error: %s", _sanitize_error_text(str(exc)))
        raise GenerationError(
            "An unexpected error occurred while generating your answer. Please try again."
        ) from None

    if not response or not getattr(response, "choices", None):
        logger.warning("OpenAI response contained no choices.")
        raise GenerationError(
            "The AI service returned an empty response. Please try asking again."
        )

    message = getattr(response.choices[0], "message", None)
    content = getattr(message, "content", None)

    if not isinstance(content, str) or not content.strip():
        logger.warning("OpenAI response contained blank content.")
        raise GenerationError(
            "The AI service returned an empty response. Please try asking again."
        )

    return content.strip()


def test_connection() -> str:
    """Send a minimal request to verify OpenAI API connectivity."""
    client = get_openai_client()
    model = get_model_name()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Reply with OK only."}],
    )
    return (response.choices[0].message.content or "").strip()


if __name__ == "__main__":
    print("OpenAI API connection status:", test_connection())
