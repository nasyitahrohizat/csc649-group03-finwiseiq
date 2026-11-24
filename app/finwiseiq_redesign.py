"""FinWiseIQ branded Gradio frontend (KAN-39 visual enhancement).

This is a stand-alone launchable UI that *reuses* app.interface.respond from
PR #18, preserving the original retrieval -> OpenAI -> citations flow.

Run from repository root: python -m app.finwiseiq_redesign
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Callable

import gradio as gr

ASSETS = Path(__file__).resolve().parent / "assets"
CSS_FILE = Path(__file__).resolve().parent / "finwiseiq_theme.css"

SUGGESTIONS = (
    "What is Murabahah financing?",
    "What is Islamic banking?",
    "What is Shariah-compliant financing?",
    "What is the difference between Islamic and conventional banking?",
)

# A safe generic message rather than exposing API key, stack trace or user data.
ERROR_MESSAGE = (
    "Sorry, something went wrong while preparing the answer. "
    "Please try again in a moment."
)
EMPTY_MESSAGE = "Please type a question about Islamic finance or Malaysian financial compliance."
ENGLISH_GREETING = "Hello! How can I help you with Islamic finance or Malaysian financial compliance?"
MALAY_GREETING = "Hai! Ada soalan tentang kewangan Islam atau pematuhan kewangan di Malaysia?"
SALAM_GREETING = (
    "Waalaikumsalam! Ada soalan tentang kewangan Islam atau pematuhan kewangan di Malaysia?"
)
GREETING_RESPONSES = {
    "hi": ENGLISH_GREETING,
    "hello": ENGLISH_GREETING,
    "hai": MALAY_GREETING,
    "salam": SALAM_GREETING,
    "assalamualaikum": SALAM_GREETING,
    "assalamu alaikum": SALAM_GREETING,
}


def _real_responder() -> Callable:
    """Import existing production response handler only when building real app.

    This avoids duplicating backend code or storing API credentials in the UI.
    """
    from app.interface import respond  # noqa: PLC0415 - existing PR #18 function

    return respond


def process_message(message: str, history: list[dict] | None, responder: Callable):
    """Append one chat turn without rewriting the backend response or citations."""
    safe_history = list(history or [])
    question = (message or "").strip()
    if not question:
        if safe_history and safe_history[-1]["role"] == "assistant":
            last_content = safe_history[-1]["content"]
            # Gradio returns previously rendered text as a list of content blocks.
            if isinstance(last_content, list) and len(last_content) == 1:
                block = last_content[0]
                if block.get("type") == "text":
                    last_content = block.get("text")
            if last_content == EMPTY_MESSAGE:
                return safe_history, ""
        return safe_history + [{"role": "assistant", "content": EMPTY_MESSAGE}], ""

    greeting = " ".join(question.casefold().strip("!?., ").split())
    answer = GREETING_RESPONSES.get(greeting)
    if answer is None:
        try:
            answer = responder(question, safe_history)
            if not isinstance(answer, str):
                answer = str(answer) if answer is not None else ERROR_MESSAGE
        except Exception:
            # Keep API keys and technical details out of user-facing errors.
            answer = ERROR_MESSAGE

    return (
        safe_history
        + [
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ],
        "",
    )


def reset_conversation():
    return [], ""


def get_logo_data_url() -> str:
    image_data = (ASSETS / "finwiseiq-logo.png").read_bytes()
    return "data:image/png;base64," + base64.b64encode(image_data).decode("ascii")


def build_app(responder: Callable | None = None) -> gr.Blocks:
    """Create full interface. Inject a test responder for offline UI checks."""
    backend = responder if responder is not None else _real_responder()
    logo = get_logo_data_url()

    with gr.Blocks(
        title="FinWiseIQ | Islamic Finance & Compliance",
    ) as demo:
        gr.HTML(
            f'''<header class="fw-nav" aria-label="FinWiseIQ brand header">
                <div class="fw-brand">
                    <img src="{logo}" alt="FinWiseIQ original logo" />
                    <div><strong>FinWiseIQ</strong><small>FINANCE • CLARITY • CONFIDENCE</small></div>
                </div>
                <div class="fw-live"><span class="fw-dot" aria-hidden="true"></span>Knowledge-powered assistant</div>
            </header>''',
            elem_id="fw-topline",
            container=False,
        )
        gr.HTML(
            '''<section class="fw-hero" aria-labelledby="fw-hero-title">
                <div class="fw-eyebrow">✦ ISLAMIC FINANCE • MALAYSIAN COMPLIANCE</div>
                <h1 id="fw-hero-title">Finance answers,<br/><em>made clearer.</em></h1>
                <p>Explore Islamic financing principles, Shariah-compliant banking,
                   AML/CFT and Malaysian financial regulations using FinWiseIQ's curated knowledge base.</p>
                <div class="fw-tags">
                    <span>✦ Islamic Finance</span><span>◇ KYC &amp; AML/CFT</span>
                    <span>◎ Malaysian Regulation</span>
                </div>
            </section>''',
            elem_id="fw-intro",
            container=False,
        )
        with gr.Column(elem_id="fw-chat-shell"):
            gr.HTML(
                '''<div class="fw-section-caption"><h2>✦ Ask FinWiseIQ</h2>
                <small>Explore • Ask • Learn</small></div>''',
                container=False,
            )
            transcript = gr.Chatbot(
                value=[],
                show_label=False,
                height=365,
                elem_id="fw-chatbox",
                placeholder="Welcome to FinWiseIQ. Choose a suggested topic or type your question below.",
                buttons=["copy"],
            )
            with gr.Row(equal_height=True, elem_id="fw-composer"):
                query = gr.Textbox(
                    show_label=False,
                    placeholder="Ask about Islamic finance or Malaysian financial compliance...",
                    lines=1,
                    max_lines=3,
                    scale=8,
                    container=False,
                    autofocus=True,
                    elem_id="fw-question",
                )
                send = gr.Button("Send ↗", variant="primary", scale=1, min_width=95, elem_id="fw-send")
                clear = gr.Button("Clear", variant="secondary", scale=1, min_width=90, elem_id="fw-clear")

            gr.HTML('<div class="fw-suggest-text">TRY A SUGGESTED QUESTION</div>', elem_id="fw-suggestions-label", container=False)
            with gr.Row(elem_classes="fw-suggestions"):
                for i, suggestion in enumerate(SUGGESTIONS):
                    chip = gr.Button(suggestion, variant="secondary", size="sm", key=f"fw-chip-{i}")
                    chip.click(
                        fn=lambda selected=suggestion: selected,
                        inputs=[],
                        outputs=query,
                        queue=False,
                    ).then(
                        fn=lambda m, h: process_message(m, h, backend),
                        inputs=[query, transcript],
                        outputs=[transcript, query],
                        show_progress="full",
                    )

            submit_action = lambda m, h: process_message(m, h, backend)
            query.submit(
                fn=submit_action,
                inputs=[query, transcript],
                outputs=[transcript, query],
                show_progress="full",
            )
            send.click(
                fn=submit_action,
                inputs=[query, transcript],
                outputs=[transcript, query],
                show_progress="full",
            )
            clear.click(fn=reset_conversation, inputs=[], outputs=[transcript, query], queue=False)

        gr.HTML(
            '''<footer class="fw-footer-text">
                <strong>Educational information only.</strong> FinWiseIQ does not provide personal financial,
                legal, regulatory or Shariah advice. Always consult a qualified professional for formal decisions.
            </footer>''',
            elem_id="fw-footer",
            container=False,
        )

    return demo


if __name__ == "__main__":
    build_app().launch(
        theme=gr.themes.Soft(primary_hue="teal", secondary_hue="cyan", neutral_hue="slate"),
        css=CSS_FILE.read_text(encoding="utf-8"),
        inbrowser=True,
        favicon_path=str(ASSETS / "finwiseiq-favicon.ico"),
        show_error=False,
    )
