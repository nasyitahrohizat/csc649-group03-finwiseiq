"""KAN-39 safe offline UI checks; these do NOT exercise the real OpenAI API."""

import gradio as gr
import pytest

from app.finwiseiq_redesign import (
    ASSETS,
    CSS_FILE,
    EMPTY_MESSAGE,
    ERROR_MESSAGE,
    SUGGESTIONS,
    build_app,
    get_logo_data_url,
    process_message,
    reset_conversation,
)


def test_normal_response_is_shown_unchanged():
    messages, text = process_message("What is murabahah?", [], lambda q, h: "Based on source [BNM, p. 3].")
    assert text == ""
    assert messages == [
        {"role": "user", "content": "What is murabahah?"},
        {"role": "assistant", "content": "Based on source [BNM, p. 3]."},
    ]


def test_question_is_trimmed():
    messages, _ = process_message("  What is riba?  ", [], lambda q, h: q)
    assert messages[0]["content"] == "What is riba?"


@pytest.mark.parametrize(
    ("message", "expected_start"),
    [
        ("Hi", "Hello!"),
        ("  HELLO!!  ", "Hello!"),
        ("Hai!", "Hai!"),
        ("Salam.", "Waalaikumsalam!"),
        ("Assalamualaikum", "Waalaikumsalam!"),
        ("Assalamu   alaikum?", "Waalaikumsalam!"),
    ],
)
def test_standalone_greetings_reply_locally(message, expected_start):
    def unexpected_responder(question, history):
        pytest.fail("A standalone greeting must not call the backend responder")

    messages, text = process_message(message, [], unexpected_responder)

    assert messages[0] == {"role": "user", "content": message.strip()}
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"].startswith(expected_start)
    assert text == ""


@pytest.mark.parametrize(
    "question",
    ["Hi, what is riba?", "Salam! Apa itu murabahah financing?"],
)
def test_finance_questions_with_greetings_use_backend(question):
    answer = "A finance answer.\n\nSources:\n- BNM"

    def responder(received_question, history):
        assert received_question == question
        return answer

    messages, _ = process_message(question, [], responder)

    assert messages[-1] == {"role": "assistant", "content": answer}


def test_empty_input_shows_guidance_without_backend_call():
    calls = []
    messages, _ = process_message("   ", [], lambda q, h: calls.append(q))
    assert not calls
    assert messages[0]["content"] == EMPTY_MESSAGE


def test_none_message_shows_guidance():
    messages, _ = process_message(None, None, lambda q, h: "no")
    assert messages[0]["content"] == EMPTY_MESSAGE


@pytest.mark.parametrize("use_gradio_history", [False, True])
def test_repeated_blank_input_preserves_history_without_duplicate_notice(use_gradio_history):
    previous = [{"role": "user", "content": "What is riba?"}]

    def unexpected_responder(question, history):
        pytest.fail("A blank submission must not call the backend responder")

    history, _ = process_message("", previous, unexpected_responder)
    assert history == previous + [{"role": "assistant", "content": EMPTY_MESSAGE}]
    if use_gradio_history:
        chatbot = gr.Chatbot()
        history = chatbot.preprocess(chatbot.postprocess(history))

    repeated_history, text = process_message(" \t\n ", history, unexpected_responder)

    assert repeated_history == history
    assert len(repeated_history) == 2
    assert text == ""


def test_blank_input_after_valid_turn_can_show_guidance_again():
    history, _ = process_message("", [], lambda q, h: None)
    history, _ = process_message("What is riba?", history, lambda q, h: "Finance answer")
    updated, _ = process_message("", history, lambda q, h: None)

    assert updated == history + [{"role": "assistant", "content": EMPTY_MESSAGE}]


def test_history_is_preserved_and_passed_to_existing_handler():
    previous = [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}]
    captured = []

    def fake(q, history):
        captured.extend(history)
        return "More info"

    new, _ = process_message("follow-up", previous, fake)
    assert captured == previous
    assert new[:2] == previous
    assert len(new) == 4
    assert len(previous) == 2  # no in-place mutation


def test_api_error_does_not_reveal_traceback_or_secret():
    def throws(q, h):
        raise RuntimeError("PRIVATE_API_KEY=top-secret")

    messages, _ = process_message("test", [], throws)
    assert messages[-1]["content"] == ERROR_MESSAGE
    assert "top-secret" not in messages[-1]["content"]


def test_no_answer_is_handled_safely():
    messages, _ = process_message("test", [], lambda q, h: None)
    assert messages[-1]["content"] == ERROR_MESSAGE


def test_out_of_scope_refusal_retained():
    refusal = "Sorry, this is outside FinWiseIQ's educational scope."
    messages, _ = process_message("Which stock should I buy?", [], lambda q, h: refusal)
    assert messages[-1]["content"] == refusal


def test_clear_conversation():
    assert reset_conversation() == ([], "")


def test_four_topic_chips():
    assert len(SUGGESTIONS) == 4
    assert all(s.endswith("?") for s in SUGGESTIONS)


def test_logo_and_css_assets_exist():
    assert (ASSETS / "finwiseiq-logo.png").is_file()
    assert (ASSETS / "finwiseiq-favicon.ico").is_file()
    assert "base64," in get_logo_data_url()
    assert CSS_FILE.is_file()


def test_gradio_components_build_without_real_backend():
    demo = build_app(lambda q, h: "Offline test only")
    assert len(demo.blocks) >= 10


def test_accessible_reduced_motion_css():
    css = CSS_FILE.read_text(encoding="utf-8")
    assert "prefers-reduced-motion" in css
    assert "@media (max-width:700px)" in css
