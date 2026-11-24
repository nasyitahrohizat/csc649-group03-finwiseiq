"""Tests for src/pipeline.py (KAN-34).

OpenAI is never called here: `monkeypatch` temporarily replaces
model.generate_answer with a fake, because the GitHub tests check has
no API key, and real calls cost money and give different answers.
"""
import pytest

from src import model, pipeline


def test_empty_question_returns_prompt():
    # A blank question never reaches retrieval or OpenAI.
    assert pipeline.process_question("   ") == pipeline.EMPTY_MESSAGE


def test_off_topic_returns_fallback_and_skips_openai(monkeypatch):
    # Pretend retrieval found nothing relevant.
    monkeypatch.setattr(pipeline, "retrieve_context", lambda q: [])
    calls = []
    # raising=False: allowed even before generate_answer exists in model.py
    monkeypatch.setattr(model, "generate_answer",
                        lambda q, c: calls.append(q), raising=False)
    assert pipeline.process_question("best pizza in KL") == pipeline.FALLBACK_MESSAGE
    assert calls == []  # proves OpenAI was NOT called


def test_relevant_question_sends_context_and_returns_answer(monkeypatch):
    seen = {}

    def fake_generate(question, context):
        seen["question"], seen["context"] = question, context
        return "Fake answer."

    monkeypatch.setattr(model, "generate_answer", fake_generate, raising=False)
    out = pipeline.process_question("What is customer due diligence?")
    # Real retrieval ran, and its context was passed to "OpenAI".
    assert seen["question"] == "What is customer due diligence?"
    assert seen["context"].startswith("[1] Q:")
    # The answer is returned with the sources underneath.
    assert out.startswith("Fake answer.")
    assert "Sources:" in out


def test_api_error_returns_friendly_message(monkeypatch):
    def broken_generate(question, context):
        raise RuntimeError("API is down")

    monkeypatch.setattr(model, "generate_answer", broken_generate, raising=False)
    # The pipeline must not crash; the user sees a polite message.
    assert pipeline.process_question("What is riba?") == pipeline.ERROR_MESSAGE


def test_format_context_numbers_each_match():
    results = [
        {"question": "Q1", "answer": "A1", "source": "S1", "source_section": "p1"},
        {"question": "Q2", "answer": "A2", "source": "S2", "source_section": "p2"},
    ]
    text = pipeline.format_context(results)
    assert text.startswith("[1] Q: Q1")
    assert "[2] Q: Q2" in text
    assert "Source: S2, p2" in text


HISTORY = [
    {"role": "user", "content": "What is murabahah?"},
    {"role": "assistant", "content": "A cost-plus sale.\n\nSources:\n- BNM Murabahah PD"},
]

ROW = {"question": "What is murabahah?", "answer": "A cost-plus sale.",
       "source": "BNM Murabahah PD", "source_section": "para 1.3"}


def fake_search(searched, matches):
    """A fake retrieve_context that records each search and only matches some."""
    def fake_retrieve(q):
        searched.append(q)
        return [ROW] if matches(q) else []
    return fake_retrieve


def test_follow_up_searches_with_previous_topic(monkeypatch):
    searched = []
    monkeypatch.setattr(pipeline, "retrieve_context",
                        fake_search(searched, lambda q: "murabahah" in q))
    monkeypatch.setattr(model, "generate_answer", lambda q, c: "Fake answer.", raising=False)
    out = pipeline.process_question("Tell me more", HISTORY)
    assert searched == ["Tell me more", "What is murabahah? Tell me more"]
    assert out.startswith("Fake answer.")


def test_chained_follow_ups_keep_the_original_topic(monkeypatch):
    searched = []
    monkeypatch.setattr(pipeline, "retrieve_context",
                        fake_search(searched, lambda q: "murabahah" in q))
    monkeypatch.setattr(model, "generate_answer", lambda q, c: "Fake answer.", raising=False)
    history = HISTORY + [
        {"role": "user", "content": "Tell me more"},
        {"role": "assistant", "content": "More about murabahah."},
    ]
    pipeline.process_question("Terangkan lagi", history)
    # "Tell me more" is skipped: the topic is still the murabahah question.
    assert searched[-1] == "What is murabahah? Terangkan lagi"


def test_comparison_keeps_the_previous_topic(monkeypatch):
    searched = []
    seen = {}
    monkeypatch.setattr(pipeline, "retrieve_context",
                        fake_search(searched, lambda q: True))

    def fake_generate(question, context):
        seen["question"] = question
        return "Fake answer."

    monkeypatch.setattr(model, "generate_answer", fake_generate, raising=False)
    pipeline.process_question("How is it different from ijarah?", HISTORY)
    assert searched == ["How is it different from ijarah?",
                        "What is murabahah? How is it different from ijarah?"]
    assert "User: What is murabahah?" in seen["question"]
    assert "CURRENT QUESTION:\nHow is it different from ijarah?" in seen["question"]
    assert "Sources:" not in seen["question"]


@pytest.mark.parametrize("message", ["How do I cook nasi lemak?", "Write me a nasi lemak recipe", "hi"])
def test_off_topic_after_a_question_still_gets_fallback(monkeypatch, message):
    searched = []
    monkeypatch.setattr(pipeline, "retrieve_context",
                        fake_search(searched, lambda q: "murabahah" in q))
    out = pipeline.process_question(message, HISTORY)
    # A new topic is NOT combined with the earlier question.
    assert searched == [message]
    assert out == pipeline.FALLBACK_MESSAGE


def test_new_question_is_sent_without_earlier_messages(monkeypatch):
    seen = {}
    monkeypatch.setattr(pipeline, "retrieve_context", lambda q: [ROW])

    def fake_generate(question, context):
        seen["question"] = question
        return "Fake answer."

    monkeypatch.setattr(model, "generate_answer", fake_generate, raising=False)
    pipeline.process_question("What is ijarah?", HISTORY)
    assert seen["question"] == "What is ijarah?"


def test_only_the_last_six_messages_are_sent():
    history = []
    for n in range(1, 11):
        history.append({"role": "user", "content": f"Question {n}"})
        history.append({"role": "assistant", "content": f"Answer {n}"})
    text = pipeline.format_history(history)
    assert text.count("\n") + 1 == pipeline.MAX_HISTORY_MESSAGES == 6
    assert "Question 8" in text and "Question 7" not in text


def test_long_messages_are_shortened():
    history = [{"role": "assistant", "content": "x" * 2000}]
    text = pipeline.format_history(history)
    assert len(text) == len("FinWiseIQ: ") + pipeline.MAX_MESSAGE_CHARS