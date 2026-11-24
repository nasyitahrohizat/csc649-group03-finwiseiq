"""Offline tests for the branded FinWiseIQ chat."""

import asyncio
from threading import Event
from unittest.mock import Mock

import gradio as gr
import pytest
from gradio.state_holder import SessionState

from app.finwiseiq_redesign import (
    ASSETS,
    CSS_FILE,
    EMPTY_MESSAGE,
    ERROR_MESSAGE,
    LOADING_MESSAGE,
    SUGGESTIONS,
    WELCOME_MESSAGE,
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
    assert reset_conversation() == ([{"role": "assistant", "content": WELCOME_MESSAGE}], "")


def test_four_topic_chips():
    assert len(SUGGESTIONS) == 4
    assert all(s.endswith("?") for s in SUGGESTIONS)


def _chat_event(demo, name):
    return next(event for event in demo.config["dependencies"] if event["api_name"] == name)


@pytest.mark.parametrize("control", ["fw-send", "fw-question", *SUGGESTIONS])
def test_submission_shows_question_before_queued_answer(control):
    response = "An answer with citations.\n\nSources:\n- BNM example"
    backend = Mock(return_value=response)
    demo = build_app(backend)
    submit = _chat_event(demo, "show_question")
    answer = _chat_event(demo, "show_answer")
    button = next(
        block for block in demo.blocks.values()
        if getattr(block, "elem_id", None) == control
        or (isinstance(block, gr.Button) and block.value == control)
    )
    trigger = "submit" if control == "fw-question" else "click"
    assert (button._id, trigger) in submit["targets"]
    assert submit["queue"] is False
    assert answer["trigger_after"] == submit["id"]
    assert answer["show_progress"] == "hidden"
    assert demo.blocks[answer["inputs"][0]].stateful

    typed = "  What is riba?  "
    expected = control if control in SUGGESTIONS else typed.strip()
    chatbot = demo.blocks[submit["outputs"][0]]
    prior = chatbot.postprocess([
        {"role": "user", "content": "Earlier question"},
        {"role": "assistant", "content": "Earlier answer"},
    ])

    async def run_submission():
        state = SessionState(demo)
        started = await demo.process_api(
            demo.fns[submit["id"]], [typed, prior.model_dump(), None],
            state=state, event_data=gr.EventData(button, None),
        )
        messages, text = started["data"]
        assert text == ""
        assert [(message["role"], message["content"][0]["text"]) for message in messages[-2:]] == [
            ("user", expected),
            ("assistant", LOADING_MESSAGE),
        ]
        backend.assert_not_called()

        finished = await demo.process_api(demo.fns[answer["id"]], [None], state=state)
        final_messages = finished["data"][0]
        assert final_messages[:-1] == messages[:-1]
        assert final_messages[-1]["role"] == "assistant"
        assert final_messages[-1]["content"][0]["text"] == response
        backend.assert_called_once_with(expected, chatbot.preprocess(prior))

    asyncio.run(run_submission())


def test_clear_discards_a_pending_answer_and_allows_another_question():
    started = Event()
    release = Event()

    def respond(question, history):
        if question == "Pending question":
            started.set()
            assert release.wait(10)
        return "Response to " + question

    demo = build_app(respond)
    submit = _chat_event(demo, "show_question")
    answer = _chat_event(demo, "show_answer")
    clear = _chat_event(demo, "clear_chat")
    cancel = next(event for event in demo.config["dependencies"] if event["cancels"])
    assert cancel["targets"] == clear["targets"]
    assert cancel["cancels"] == [answer["id"]]
    send = next(block for block in demo.blocks.values() if getattr(block, "elem_id", None) == "fw-send")

    async def run_clear():
        state = SessionState(demo)

        async def send_question(question, history=None):
            return await demo.process_api(
                demo.fns[submit["id"]], [question, history or [], None],
                state=state, event_data=gr.EventData(send, None),
            )

        await send_question("Pending question")
        pending = asyncio.create_task(
            demo.process_api(demo.fns[answer["id"]], [None], state=state)
        )
        try:
            assert await asyncio.to_thread(started.wait, 5)
            skipped = await send_question("Second click")
            assert skipped["data"] == [gr.skip(), gr.skip()]
            duplicate = await demo.process_api(demo.fns[answer["id"]], [None], state=state)
            assert duplicate["data"] == [gr.skip()]
            cleared = await demo.process_api(demo.fns[clear["id"]], [None], state=state)
            messages, field = cleared["data"]
            assert field == ""
            assert len(messages) == 1
            assert messages[0]["role"] == "assistant"
            assert messages[0]["content"][0]["text"] == WELCOME_MESSAGE
            await send_question("Fresh question", messages)
        finally:
            release.set()

        assert (await pending)["data"] == [gr.skip()]
        fresh = await demo.process_api(demo.fns[answer["id"]], [None], state=state)
        assert [message["content"][0]["text"] for message in fresh["data"][0]] == [
            WELCOME_MESSAGE, "Fresh question", "Response to Fresh question"
        ]

    asyncio.run(run_clear())


def test_welcome_and_clear_leave_no_backend_history(monkeypatch):
    from src import pipeline

    first_question = "What is Murabahah?"
    review_row = {
        "question": first_question,
        "answer": "Murabahah is a cost-plus sale.",
        "source": "BNM example",
        "source_section": "paragraph 1",
    }
    retrieve = Mock(side_effect=lambda query: [review_row] if first_question in query else [])
    generate = Mock(return_value=review_row["answer"])
    monkeypatch.setattr(pipeline, "retrieve_context", retrieve)
    monkeypatch.setattr(pipeline.model, "generate_answer", generate)
    demo = build_app()
    submit = _chat_event(demo, "show_question")
    answer = _chat_event(demo, "show_answer")
    clear = _chat_event(demo, "clear_chat")
    chatbot = demo.blocks[submit["outputs"][0]]
    initial = chatbot.get_config()["value"]
    assert [(msg["role"], msg["content"][0]["text"]) for msg in initial] == [
        ("assistant", WELCOME_MESSAGE)
    ]

    async def run_welcome_and_clear():
        state = SessionState(demo)
        event = gr.EventData(demo.blocks[submit["targets"][0][0]], None)

        async def turn(question, history):
            await demo.process_api(
                demo.fns[submit["id"]], [question, history, None], state=state, event_data=event,
            )
            reply = await demo.process_api(demo.fns[answer["id"]], [None], state=state)
            return reply["data"][0]

        history = await turn(first_question, initial)
        assert "Sources:" in history[-1]["content"][0]["text"]
        assert generate.call_args.args[0] == first_question
        history = await turn("Tell me more", history)
        prompt = generate.call_args.args[0]
        assert "User: " + first_question in prompt
        assert WELCOME_MESSAGE not in prompt
        assert LOADING_MESSAGE not in prompt

        cleared = await demo.process_api(demo.fns[clear["id"]], [None], state=state)
        assert cleared["data"] == [initial, ""]
        retrieve.reset_mock()
        generate.reset_mock()
        fresh = await turn("Tell me more", cleared["data"][0])
        assert fresh[-1]["content"][0]["text"] == pipeline.FALLBACK_MESSAGE
        retrieve.assert_called_once_with("Tell me more")
        generate.assert_not_called()

    asyncio.run(run_welcome_and_clear())


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
