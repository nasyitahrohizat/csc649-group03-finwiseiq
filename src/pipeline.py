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
    """The user's last question that got a real answer (one with sources).

    Skips follow-ups ("tell me more") and chit-chat that only got the
    fallback or a greeting ("oh ok", "hi"), so they never replace the topic.
    """
    messages = [m for m in (history or []) if isinstance(m, dict)]
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].get("role") != "user":
            continue
        text = _message_text(messages[i].get("content")).strip()
        reply = messages[i + 1] if i + 1 < len(messages) else {}
        answered = "\n\nSources:" in _message_text(reply.get("content"))
        if text and answered and not is_follow_up(text):
            return text
    return ""

# Short replies like "oh ok" or "thanks" are small talk, not questions.
ACKNOWLEDGEMENTS = {"ok", "okay", "oh ok", "oh okay", "i see", "oh i see", "got it",
                    "noted", "alright", "cool", "nice", "great"}
ACKNOWLEDGEMENTS_MS = {"baik", "baiklah", "faham", "oh faham", "ok faham", "oh baru faham"}
THANKS = {"thanks", "thank you", "thank you so much", "thanks a lot", "thx", "tq", "tqvm"}
THANKS_MS = {"terima kasih", "terima kasih banyak", "ribuan terima kasih"}
GOODBYES = {"bye", "bye bye", "goodbye"}
GOODBYES_MS = {"selamat tinggal", "jumpa lagi"}
# Thinking sounds of any length: "hmm", "hmmmm", "umm", "erm", "uh".
HESITATION = re.compile(r"h+m+|u+m+|e+r+m*|u+h+")


# Common Malay words, used to tell if the user has been writing in Malay.
MALAY_WORDS = {
    "apa", "itu", "ini", "tu", "ni", "adalah", "ialah", "boleh", "saya", "aku",
    "macam", "mana", "bagaimana", "kenapa", "mengapa", "maksud", "dalam", "untuk",
    "dengan", "yang", "tak", "tidak", "nak", "ada", "dan", "atau", "bagi", "kah",
    "terangkan", "jelaskan", "lagi", "contoh", "faham", "baik", "kewangan",
    "hai", "salam", "assalamualaikum", "terima", "kasih", "selamat", "jumpa",
}


def conversation_is_malay(history: list[dict] | None) -> bool:
    """True if the user's last real message (not just "hmm") was in Malay."""
    for msg in reversed(history or []):
        if isinstance(msg, dict) and msg.get("role") == "user":
            words = [w for w in _words(_message_text(msg.get("content")))
                     if not HESITATION.fullmatch(w)]
            if words:
                return bool(set(words) & MALAY_WORDS)
    return False

def small_talk_reply(question: str, history: list[dict] | None = None) -> str:
    """A friendly reply to "oh ok", "thanks" or "bye"; "" if it is not small talk.

    The reply has no sources, so last_topic_question() skips it and a later
    "tell me more" still refers to the last real question.
    """
    words = _words(question)
    # Drop thinking sounds, so "hmm ok" is treated like "ok".
    text = " ".join(w for w in words if not HESITATION.fullmatch(w))
    has_topic = bool(last_topic_question(history))
        # "ok", "hmm", "tq" and "bye" are used in both languages, so they get
    # a Malay reply if the user has been writing in Malay.
    malay = conversation_is_malay(history)
    if words and not text:  # only thinking sounds, e.g. "hmm" or "umm"
        if malay:
            if has_topic:
                return ("Tak apa, ambil masa anda! 😊 Kalau ada yang kurang jelas, "
                        'taip "terangkan lagi" atau "contoh".')
            return ("Tak apa, ambil masa anda! 😊 Anda boleh tanya soalan seperti "
                    '"Apa itu murabahah?"')
        if has_topic:
            return ("No worries, take your time! 😊 If something wasn't clear, "
                    'say "tell me more" or "explain it more simply".')
        return ("No worries, take your time! 😊 You can ask me things like "
                '"What is murabahah?" or "What is customer due diligence?"')
    if text in ACKNOWLEDGEMENTS_MS or (text in ACKNOWLEDGEMENTS and malay):
        more = ' Atau taip "terangkan lagi" untuk penjelasan lanjut.' if has_topic else ""
        return "Baik! 😊 Ada apa-apa lagi yang boleh saya bantu?" + more
    if text in ACKNOWLEDGEMENTS:
        more = ' Or say "tell me more" and I\'ll explain further.' if has_topic else ""
        return "Glad that helps! 😊 Is there anything else I can help you with?" + more
    if text in THANKS_MS or (text in THANKS and malay):
        return "Sama-sama! 😊 Tanya sahaja jika ada soalan lain."
    if text in THANKS:
        return "You're welcome! 😊 Feel free to ask if you have any other questions."
    if text in GOODBYES_MS or (text in GOODBYES and malay):
        return "Selamat tinggal! 👋 Terima kasih kerana menggunakan FinWiseIQ."
    if text in GOODBYES:
        return "Goodbye! 👋 Thanks for using FinWiseIQ. Come back anytime."
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

    reply = small_talk_reply(question, history)
    if reply:
        return reply  # small talk: no search and no OpenAI call

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