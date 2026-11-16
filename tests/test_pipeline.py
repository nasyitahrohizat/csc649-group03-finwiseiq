"""Tests for src/pipeline.py (KAN-34).

OpenAI is never called here: `monkeypatch` temporarily replaces
model.generate_answer with a fake, because the GitHub tests check has
no API key, and real calls cost money and give different answers.
"""
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
