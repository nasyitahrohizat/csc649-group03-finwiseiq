"""FinWiseIQ pipeline: question -> retrieval -> OpenAI answer (KAN-34).

process_question() is the single entry point the Gradio app calls.
It never raises: it always returns text for the user.
"""
import logging
import re
from src import model
from src.retrieval import retrieve_context

logger = logging.getLogger(__name__)

EMPTY_MESSAGE = "Please enter a question."
FALLBACK_MESSAGE = (
    "Sorry, I can only answer questions about Islamic finance and Malaysian "
    "financial compliance (AML/CFT, KYC/CDD and regulation), and I could not "
    "find relevant information for that question. Please try rephrasing it."
)
ERROR_MESSAGE = (
    "Sorry, the answer service is unavailable right now. Please try again later."
)


def format_context(results: list[dict]) -> str:
    """Turn retrieved matches into the numbered text block sent to OpenAI."""
    blocks = []
    for n, r in enumerate(results, start=1):
        # this is the code that formats the retrieved results into a numbered list for OpenAI
        blocks.append(
            f"[{n}] Q: {r['question']}\n"
            f"    A: {r['answer']}\n"
            f"    Source: {r['source']}, {r['source_section']}"
        )
    return "\n".join(blocks)


def format_sources(results: list[dict]) -> str:
    """List each source once, so the user can check where the answer came from."""
    sources = []
    for r in results:
        s = f"{r['source']} ({r['source_section']})"
        if s not in sources:
            sources.append(s)
    return "\n".join(f"- {s}" for s in sources)


# Words that show a message refers back to the earlier question
# (English and Malay), e.g. "tell me more", "give an example", "terangkan lagi".
FOLLOW_UP_WORDS = {
    "it", "its", "this", "that", "these", "those", "they", "them",
    "more", "example", "examples", "elaborate", "explain", "why", "how",
    "about", "also", "else", "difference", "lagi", "contoh", "tu", "ni",
}


def _message_text(content) -> str:
    """Gradio may store a message as plain text or as a list of text parts."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(
            part.get("text", "") for part in content if isinstance(part, dict)
        )
    return ""


def last_user_question(history: list[dict] | None) -> str:
    """The user's previous question, used when a follow-up is too vague to search alone."""
    for msg in reversed(history or []):
        if isinstance(msg, dict) and msg.get("role") == "user":
            text = _message_text(msg.get("content")).strip()
            if text:
                return text
    return ""


def is_follow_up(question: str) -> bool:
    """True if the message seems to refer back to the earlier question."""
    words = set(re.findall(r"[a-z]+", question.lower()))
    return bool(words & FOLLOW_UP_WORDS)

def process_question(question: str, history: list[dict] | None = None) -> str:
    """Answer a user question, using earlier messages for follow-ups. Never raises."""
    if not question or not question.strip():
        return EMPTY_MESSAGE
    question = question.strip()

    results = retrieve_context(question)
    if not results:
        # A follow-up such as "tell me more" has no topic of its own,
        # so search again together with the previous question.
        previous = last_user_question(history)
        if previous and is_follow_up(question):
            results = retrieve_context(f"{previous} {question}")
    if not results:
        return FALLBACK_MESSAGE  # off-topic: OpenAI is NOT called

    context = format_context(results)
    try:
        answer = model.generate_answer(question, context)
    except Exception as exc:  # API failure, timeout, missing key, etc.
        logger.warning("Answer generation failed: %s", type(exc).__name__)
        return ERROR_MESSAGE

    return f"{answer}\n\nSources:\n{format_sources(results)}"