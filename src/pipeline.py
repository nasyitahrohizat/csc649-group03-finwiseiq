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

MAX_HISTORY_MESSAGES = 6  # the last 3 questions and 3 answers
MAX_MESSAGE_CHARS = 500   # keep each earlier message short

# Words that point back to something said earlier ("is IT halal?", "apa TU?").
REFERENCE_WORDS = {"it", "its", "this", "that", "these", "those", "they", "them", "tu", "ni"}

# A pure follow-up uses ONLY these words: it asks for more about the earlier
# topic and brings no new topic of its own (English and Malay).
FOLLOW_UP_WORDS = REFERENCE_WORDS | {
    "tell", "me", "more", "again", "give", "an", "a", "another", "example", "examples",
    "can", "could", "you", "please", "explain", "elaborate", "detail", "details",
    "why", "how", "what", "does", "do", "is", "mean", "means", "and", "so", "ok",
    "okay", "also", "else", "further", "simpler", "simply", "in", "words", "other",
    "about", "i", "don", "t", "understand",
    "lagi", "contoh", "terangkan", "jelaskan", "boleh", "bagi", "apa", "maksud",
    "kenapa", "macam", "mana", "sikit", "lebih", "lanjut", "tak", "faham",
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


def _words(text: str) -> list[str]:
    """Lower-case words only, e.g. "Tell me more!" -> ["tell", "me", "more"]."""
    return re.findall(r"[a-z]+", text.lower())


def is_follow_up(question: str) -> bool:
    """True if the message only asks for more about the earlier topic.

    "Tell me more" or "terangkan lagi" -> True.
    "How do I cook nasi lemak?" -> False ("cook", "nasi", "lemak" are a new topic).
    """
    words = _words(question)
    return bool(words) and all(w in FOLLOW_UP_WORDS for w in words)


def refers_back(question: str) -> bool:
    """True if the message points back with a word such as "it" or "that"."""
    return bool(set(_words(question)) & REFERENCE_WORDS)


def last_topic_question(history: list[dict] | None) -> str:
    """The user's last real question, skipping follow-ups such as "tell me more"."""
    for msg in reversed(history or []):
        if isinstance(msg, dict) and msg.get("role") == "user":
            text = _message_text(msg.get("content")).strip()
            if text and not is_follow_up(text):
                return text
    return ""


def format_history(history: list[dict] | None) -> str:
    """Turn the last few chat messages into short text for OpenAI (sources removed)."""
    lines = []
    for msg in (history or [])[-MAX_HISTORY_MESSAGES:]:
        if not isinstance(msg, dict) or msg.get("role") not in ("user", "assistant"):
            continue
        text = _message_text(msg.get("content")).split("\n\nSources:")[0].strip()
        if text:
            speaker = "User" if msg["role"] == "user" else "FinWiseIQ"
            lines.append(f"{speaker}: {text[:MAX_MESSAGE_CHARS]}")
    return "\n".join(lines)


def process_question(question: str, history: list[dict] | None = None) -> str:
    """Answer a user question, using earlier messages for follow-ups. Never raises."""
    if not question or not question.strip():
        return EMPTY_MESSAGE
    question = question.strip()

    results = retrieve_context(question)
    topic = last_topic_question(history)
    uses_history = False
    if topic and (is_follow_up(question) or (results and refers_back(question))):
        # "Tell me more" has no topic of its own, and "How is it different
        # from ijarah?" needs the earlier topic too, so search with both.
        combined = retrieve_context(f"{topic} {question}")
        if combined:
            results, uses_history = combined, True
    if not results:
        return FALLBACK_MESSAGE  # off-topic: OpenAI is NOT called

    context = format_context(results)
    if uses_history:
        # Only follow-ups get the earlier conversation; new questions are sent alone.
        question_for_model = (
            f"CONVERSATION SO FAR:\n{format_history(history)}\n\n"
            f"CURRENT QUESTION:\n{question}"
        )
    else:
        question_for_model = question

    try:
        answer = model.generate_answer(question_for_model, context)
    except Exception as exc:  # API failure, timeout, missing key, etc.
        logger.warning("Answer generation failed: %s", type(exc).__name__)
        return ERROR_MESSAGE

    return f"{answer}\n\nSources:\n{format_sources(results)}"