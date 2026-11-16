"""Unit tests for src/model.py using a mocked OpenAI client."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import pytest
from openai import OpenAIError

from src.model import GenerationError, generate_answer
from src.prompt import SYSTEM_PROMPT


def _make_mock_response(text: str | None):
    """Build a minimal mock object mimicking OpenAI ChatCompletion response."""
    message = SimpleNamespace(content=text)
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice])


@patch("src.model.get_model_name", return_value="gpt-4o-mini")
@patch("src.model.get_openai_client")
def test_generate_answer_success(mock_get_client, _mock_model):
    """generate_answer passes system prompt + context and returns clean text."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_mock_response(
        "  Murabahah is a cost-plus financing contract.  \n"
    )
    mock_get_client.return_value = mock_client

    question = "What is Murabahah?"
    context = "[1] Q: What is Murabahah? A: Cost-plus sale. Source: BNM, Sec 2"

    result = generate_answer(question, context)

    assert result == "Murabahah is a cost-plus financing contract."
    mock_client.chat.completions.create.assert_called_once()
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "gpt-4o-mini"
    assert call_kwargs["messages"][0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert context in call_kwargs["messages"][1]["content"]
    assert question in call_kwargs["messages"][1]["content"]


@patch("src.model.get_openai_client")
def test_generate_answer_missing_context_raises_value_error(mock_get_client):
    """Missing or whitespace-only context raises ValueError without calling API."""
    with pytest.raises(ValueError, match="Context"):
        generate_answer("What is Riba?", "   ")
    mock_get_client.assert_not_called()


@patch("src.model.get_openai_client")
def test_generate_answer_missing_question_raises_value_error(mock_get_client):
    """Missing or whitespace-only question raises ValueError without calling API."""
    with pytest.raises(ValueError, match="Question"):
        generate_answer("", "[1] Q: Sample A: Sample Source: BNM, Sec 1")
    mock_get_client.assert_not_called()


@patch("src.model.get_model_name", return_value="gpt-4o-mini")
@patch("src.model.get_openai_client")
def test_generate_answer_api_error_raises_generation_error(mock_get_client, _mock_model):
    """OpenAI API errors are wrapped and raised as GenerationError."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = OpenAIError("Rate limit exceeded")
    mock_get_client.return_value = mock_client

    with pytest.raises(GenerationError, match="Failed to generate answer"):
        generate_answer("What is Takaful?", "[1] Q: Takaful A: Mutual protection Source: BNM, Sec 1")


@patch("src.model.get_model_name", return_value="gpt-4o-mini")
@patch("src.model.get_openai_client")
def test_generate_answer_invalid_response_format_raises_generation_error(
    mock_get_client, _mock_model
):
    """Empty or malformed API responses raise GenerationError."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = SimpleNamespace(choices=[])
    mock_get_client.return_value = mock_client

    with pytest.raises(GenerationError, match="no choices"):
        generate_answer("What is Gharar?", "[1] Q: Gharar A: Uncertainty Source: BNM, Sec 1")
