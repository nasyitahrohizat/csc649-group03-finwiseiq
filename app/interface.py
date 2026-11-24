
from src.pipeline import process_question

def get_backend_answer(message, history=None):
    """Send the question and conversation history to the RAG pipeline."""
    return process_question(message, history)

def respond(message, history):
    """Handle user questions and backend errors safely."""

    if not isinstance(message, str) or not message.strip():
        return "Please type a question."

    try:
        reply = get_backend_answer(message.strip(), history)

        if not isinstance(reply, str) or not reply.strip():
            return "Sorry, I couldn't get an answer right now. Please try again."

        return reply

    except Exception:
        return "Sorry, something went wrong. Please try again later."
