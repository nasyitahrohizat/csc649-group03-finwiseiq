"""Backend OpenAI API client and context-based answer generation for FinWiseIQ."""

import os
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

from src.prompt import SYSTEM_PROMPT

load_dotenv()


class GenerationError(Exception):
    """Raised when OpenAI answer generation fails or returns an invalid response."""


def get_openai_client() -> OpenAI:
    """Return an authenticated OpenAI client using environment variables."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your_openai_api_key_here":
        raise RuntimeError(
            "OPENAI_API_KEY is missing or still set to the placeholder value in .env."
        )
    return OpenAI(api_key=api_key, timeout=30)


def get_model_name() -> str:
    """Return the configured OpenAI model ID from environment variables."""
    model = os.getenv("OPENAI_MODEL", "").strip()
    if not model:
        raise RuntimeError("OPENAI_MODEL is not configured in the environment.")
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
        GenerationError: If the OpenAI API call fails or returns an invalid response.
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
            temperature=0.2,
        )
    except OpenAIError as exc:
        raise GenerationError("Failed to generate answer from OpenAI API.") from exc
    except Exception as exc:
        raise GenerationError("Unexpected error during answer generation.") from exc

    if not response or not getattr(response, "choices", None):
        raise GenerationError("OpenAI response contained no choices.")

    message = getattr(response.choices[0], "message", None)
    content = getattr(message, "content", None)

    if not isinstance(content, str) or not content.strip():
        raise GenerationError("OpenAI response contained empty content.")

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
