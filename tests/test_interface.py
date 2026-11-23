"""Frontend tests for the FinWiseIQ Gradio chatbot."""

from unittest.mock import Mock

import pytest

import app.interface as interface


@pytest.mark.parametrize("message", ["", "   ", "\n\t", None, 123])
def test_empty_input(message, monkeypatch):
    """Empty or invalid input should be rejected politely."""
    fake_backend = Mock(return_value="Mock answer")
    monkeypatch.setattr(interface, "mock_backend", fake_backend)

    result = interface.respond(message, [])

    assert result == "Please type a question."
    fake_backend.assert_not_called()


def test_chat_input_and_response_display(monkeypatch):
    """A valid question should produce the mock backend response."""
    fake_backend = Mock(return_value="Murabahah is a cost-plus sale.")
    monkeypatch.setattr(interface, "mock_backend", fake_backend)

    result = interface.respond("What is Murabahah?", [])

    assert result == "Murabahah is a cost-plus sale."
    fake_backend.assert_called_once_with("What is Murabahah?")


def test_chat_history(monkeypatch):
    """Previous chat history should not prevent a new response."""
    fake_backend = Mock(return_value="Mock follow-up answer")
    monkeypatch.setattr(interface, "mock_backend", fake_backend)

    history = [
        {"role": "user", "content": "What is Islamic banking?"},
        {"role": "assistant", "content": "Previous mock answer."},
    ]

    result = interface.respond("Tell me more.", history)

    assert result == "Mock follow-up answer"


def test_backend_failure(monkeypatch):
    """Backend exceptions should produce a friendly error message."""
    fake_backend = Mock(side_effect=RuntimeError("Secret backend error"))
    monkeypatch.setattr(interface, "mock_backend", fake_backend)

    result = interface.respond("What is zakat?", [])

    assert result == "Sorry, something went wrong. Please try again later."
    assert "Secret backend error" not in result


@pytest.mark.parametrize("reply", ["", "   ", None, 123])
def test_invalid_backend_response(reply, monkeypatch):
    """Empty or invalid backend responses should be handled safely."""
    fake_backend = Mock(return_value=reply)
    monkeypatch.setattr(interface, "mock_backend", fake_backend)

    result = interface.respond("What is Islamic finance?", [])

    assert result == (
        "Sorry, I couldn't get an answer right now. Please try again."
    )