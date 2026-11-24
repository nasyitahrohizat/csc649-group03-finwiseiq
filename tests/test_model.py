"""Unit tests for src/model.py covering generation, error handling, and validation."""

import logging
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import httpx
import pytest
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    NotFoundError,
    OpenAIError,
    RateLimitError,
)

from src.model import GenerationError, generate_answer
from src.prompt import SYSTEM_PROMPT

SAMPLE_QUESTION = "What is Takaful?"
SAMPLE_CONTEXT = "[1] Q: What is Takaful? A: Mutual protection scheme. Source: BNM, Sec 1"


def _make_mock_response(text: str | None):
    """Build a minimal mock object mimicking OpenAI ChatCompletion response."""
    message = SimpleNamespace(content=text)
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice])


def _dummy_request() -> httpx.Request:
    return httpx.Request("POST", "https://api.openai.com/v1/chat/completions")


def _dummy_response(status_code: int) -> httpx.Response:
    return httpx.Response(status_code=status_code, request=_dummy_request())


@patch("src.model.get_model_name", return_value="gpt-4o-mini")
@patch("src.model.get_openai_client")
def test_generate_answer_success(mock_get_client, _mock_model):
    """generate_answer passes system prompt + context and returns clean text."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_mock_response(
        "  Takaful is based on mutual assistance.  \n"
    )
    mock_get_client.return_value = mock_client

    result = generate_answer(SAMPLE_QUESTION, SAMPLE_CONTEXT)

    assert result == "Takaful is based on mutual assistance."
    mock_client.chat.completions.create.assert_called_once()
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "gpt-4o-mini"
    assert call_kwargs["messages"][0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert SAMPLE_CONTEXT in call_kwargs["messages"][1]["content"]
    assert SAMPLE_QUESTION in call_kwargs["messages"][1]["content"]


@patch("src.model.get_openai_client")
def test_generate_answer_missing_context_raises_value_error(mock_get_client):
    """Missing or whitespace-only context raises ValueError without calling API."""
    with pytest.raises(ValueError, match="Context"):
        generate_answer(SAMPLE_QUESTION, "   ")
    mock_get_client.assert_not_called()


@patch("src.model.get_openai_client")
def test_generate_answer_missing_question_raises_value_error(mock_get_client):
    """Missing or whitespace-only question raises ValueError without calling API."""
    with pytest.raises(ValueError, match="Question"):
        generate_answer("", SAMPLE_CONTEXT)
    mock_get_client.assert_not_called()


@patch("src.model.get_model_name", return_value="gpt-4o-mini")
@patch("src.model.get_openai_client")
def test_generate_answer_timeout_raises_friendly_error(mock_get_client, _mock_model):
    """APITimeoutError returns a friendly GenerationError without internal details."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = APITimeoutError(
        request=_dummy_request()
    )
    mock_get_client.return_value = mock_client

    with pytest.raises(GenerationError) as exc_info:
        generate_answer(SAMPLE_QUESTION, SAMPLE_CONTEXT)

    assert "took too long" in str(exc_info.value).lower()
    assert exc_info.value.__cause__ is None


@patch("src.model.get_model_name", return_value="gpt-4o-mini")
@patch("src.model.get_openai_client")
def test_generate_answer_auth_error_redacts_api_key(
    mock_get_client, _mock_model, monkeypatch, caplog
):
    """AuthenticationError never leaks API keys in user message or logs."""
    secret_key = "sk-test-supersecretkey12345"
    monkeypatch.setenv("OPENAI_API_KEY", secret_key)

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = AuthenticationError(
        message=f"Incorrect API key provided: {secret_key}",
        response=_dummy_response(401),
        body=None,
    )
    mock_get_client.return_value = mock_client

    with caplog.at_level(logging.ERROR):
        with pytest.raises(GenerationError) as exc_info:
            generate_answer(SAMPLE_QUESTION, SAMPLE_CONTEXT)

    assert "authentication issue" in str(exc_info.value).lower()
    assert secret_key not in str(exc_info.value)
    assert secret_key not in caplog.text
    assert "OpenAI authentication failed." in caplog.text
    assert exc_info.value.__cause__ is None


@patch("src.model.get_model_name", return_value="gpt-4o-mini")
@patch("src.model.get_openai_client")
def test_generate_answer_rate_limit_raises_friendly_error(mock_get_client, _mock_model):
    """RateLimitError returns a friendly GenerationError."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RateLimitError(
        message="Rate limit exceeded",
        response=_dummy_response(429),
        body=None,
    )
    mock_get_client.return_value = mock_client

    with pytest.raises(GenerationError) as exc_info:
        generate_answer(SAMPLE_QUESTION, SAMPLE_CONTEXT)

    assert "busy" in str(exc_info.value).lower()
    assert exc_info.value.__cause__ is None


@patch("src.model.get_model_name", return_value="nonexistent-model")
@patch("src.model.get_openai_client")
def test_generate_answer_unavailable_model_raises_friendly_error(
    mock_get_client, _mock_model
):
    """NotFoundError for unavailable model returns a friendly GenerationError."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = NotFoundError(
        message="The model `nonexistent-model` does not exist",
        response=_dummy_response(404),
        body=None,
    )
    mock_get_client.return_value = mock_client

    with pytest.raises(GenerationError) as exc_info:
        generate_answer(SAMPLE_QUESTION, SAMPLE_CONTEXT)

    assert "unavailable" in str(exc_info.value).lower()
    assert exc_info.value.__cause__ is None


@patch("src.model.get_model_name", return_value="gpt-4o-mini")
@patch("src.model.get_openai_client")
def test_generate_answer_connection_and_generic_errors(mock_get_client, _mock_model):
    """Connection and generic OpenAI errors are masked with friendly messages."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = APIConnectionError(
        request=_dummy_request()
    )
    mock_get_client.return_value = mock_client

    with pytest.raises(GenerationError, match="connect"):
        generate_answer(SAMPLE_QUESTION, SAMPLE_CONTEXT)

    mock_client.chat.completions.create.side_effect = OpenAIError("Internal server trace")
    with pytest.raises(GenerationError, match="unexpected error"):
        generate_answer(SAMPLE_QUESTION, SAMPLE_CONTEXT)


@patch("src.model.get_model_name", return_value="gpt-4o-mini")
@patch("src.model.get_openai_client")
def test_generate_answer_empty_responses_raise_friendly_error(
    mock_get_client, _mock_model
):
    """Empty choices list or blank message content raises a friendly GenerationError."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = SimpleNamespace(choices=[])
    mock_get_client.return_value = mock_client

    with pytest.raises(GenerationError, match="empty response"):
        generate_answer(SAMPLE_QUESTION, SAMPLE_CONTEXT)

    mock_client.chat.completions.create.return_value = _make_mock_response("   ")
    with pytest.raises(GenerationError, match="empty response"):
        generate_answer(SAMPLE_QUESTION, SAMPLE_CONTEXT)


SAMPLE_CSV_CONTEXT = (
    '[1] ID: IFF-001 | Category: Islamic Finance Fundamentals | '
    'Q: What does Shariah-compliant mean in finance? | '
    'A: A Shariah-compliant product follows Islamic law, avoiding riba, maysir, and gharar. | '
    'Source: BNM Policy Document: Shariah Governance (BNM/RH/PD 028-100, 20 Sep 2019), PD para 1.3\n'
    '[2] ID: IFF-002 | Category: Islamic Finance Fundamentals | '
    'Q: What is riba and why do Islamic banks avoid it? | '
    'A: Riba refers to interest. Islamic banks use trade or partnership contracts instead. | '
    'Source: BNM website: Islamic Banking & Takaful, Overview'
)


@patch("src.model.get_model_name", return_value="gpt-4o-mini")
@patch("src.model.get_openai_client")
def test_generate_answer_relevant_csv_context(mock_get_client, _mock_model):
    """Relevant question with CSV-formatted context returns a grounded answer."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_mock_response(
        "A Shariah-compliant financial product follows Islamic law by avoiding riba, "
        "maysir, and gharar (Source: BNM Policy Document: Shariah Governance, PD para 1.3)."
    )
    mock_get_client.return_value = mock_client

    answer = generate_answer(
        "What does Shariah-compliant mean in finance?",
        SAMPLE_CSV_CONTEXT,
    )

    assert "Shariah-compliant" in answer
    assert "riba" in answer
    sent_messages = mock_client.chat.completions.create.call_args.kwargs["messages"]
    assert "IFF-001" in sent_messages[1]["content"]


@patch("src.model.get_model_name", return_value="gpt-4o-mini")
@patch("src.model.get_openai_client")
def test_generate_answer_insufficient_context(mock_get_client, _mock_model):
    """Question not covered by retrieved CSV context produces a safe fallback answer."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_mock_response(
        "The provided FinWiseIQ knowledge base context does not contain enough "
        "information on Sukuk structuring requirements."
    )
    mock_get_client.return_value = mock_client

    answer = generate_answer(
        "What are the exact capital adequacy ratios for Sukuk issuance?",
        SAMPLE_CSV_CONTEXT,
    )

    assert "does not contain enough information" in answer.lower()


@patch("src.model.get_model_name", return_value="gpt-4o-mini")
@patch("src.model.get_openai_client")
def test_generate_answer_out_of_scope_question(mock_get_client, _mock_model):
    """Out-of-scope question is politely declined under FinWiseIQ system boundaries."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_mock_response(
        "I can only answer educational questions related to Islamic finance and "
        "Malaysian financial compliance based on the FinWiseIQ knowledge base."
    )
    mock_get_client.return_value = mock_client

    answer = generate_answer(
        "Which stock will go up tomorrow on Bursa Malaysia?",
        SAMPLE_CSV_CONTEXT,
    )

    assert "islamic finance" in answer.lower()
