import gradio as gr

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


demo = gr.ChatInterface(
    fn=respond,
    show_progress="full",
    title="FinWiseIQ",
    examples=[
        "What is Murabahah financing?",
        "What is Islamic banking?",
        "What is Shariah-compliant financing?",
        "What is the difference between Islamic and conventional banking?"

    ],
    textbox=gr.Textbox(
        placeholder="Ask a question about Islamic finance or Malaysian financial compliance...",
        lines=1,
        max_lines=3,
    ),
    description=(
        "An AI-powered Islamic Finance and Malaysian Financial "
        "Compliance Assistant.\n\n"
        "Educational information only. Not professional financial, "
        "legal, regulatory or Shariah advice."
    ),
)


if __name__ == "__main__":
    demo.launch()
