"""FinWiseIQ pipeline: question -> retrieval -> OpenAI answer (KAN-34).

process_question() is the single entry point the Gradio app calls.
It never raises: it always returns text for the user.
"""
import logging

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


def process_question(question: str) -> str:
    """Answer a user question. Always returns text, never raises."""
    if not question or not question.strip():
        return EMPTY_MESSAGE

    results = retrieve_context(question)
    if not results:
        return FALLBACK_MESSAGE  # off-topic: OpenAI is NOT called

    context = format_context(results)
    try:
        answer = model.generate_answer(question.strip(), context)
    except Exception as exc:  # API failure, timeout, missing key, etc.
        logger.warning("Answer generation failed: %s", type(exc).__name__)
        return ERROR_MESSAGE

    return f"{answer}\n\nSources:\n{format_sources(results)}"
