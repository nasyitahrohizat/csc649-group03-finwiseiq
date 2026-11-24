"""KAN-39 safe offline UI checks; these do NOT exercise the real OpenAI API."""

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


def test_empty_input_shows_guidance_without_backend_call():
    calls = []
    messages, _ = process_message("   ", [], lambda q, h: calls.append(q))
    assert not calls
    assert messages[0]["content"] == EMPTY_MESSAGE


def test_none_message_shows_guidance():
    messages, _ = process_message(None, None, lambda q, h: "no")
    assert messages[0]["content"] == EMPTY_MESSAGE


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
