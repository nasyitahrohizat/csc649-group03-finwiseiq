
from src.pipeline import process_question

def get_backend_answer(message):
    """Send the question to the RAG pipeline (retrieval + OpenAI) and return the reply."""
    return process_question(message)

def respond(message, history):
    """Handle user questions and backend errors safely."""

    if not isinstance(message, str) or not message.strip():
        return "Please type a question."

    try:
        reply = get_backend_answer(message.strip())

        if not isinstance(reply, str) or not reply.strip():
            return "Sorry, I couldn't get an answer right now. Please try again."

        return reply

    except Exception:
        return "Sorry, something went wrong. Please try again later."
