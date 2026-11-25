# Pipeline Test Results (KAN-34)

End-to-end manual test of `src/pipeline.py` → `process_question()` using the
real OpenAI API (retrieval → context formatting → generation → sources).

- **Date:** 24 Nov 2026
- **Branch:** `feature/backend-integration`
- **Model:** `gpt-6-luna` (from `OPENAI_MODEL` in `.env`)
- **Retrieval:** `all-MiniLM-L6-v2`, TOP_K = 3, THRESHOLD = 0.45
- **Command pattern:**
  `python -c "from src.pipeline import process_question as p; print(p('<question>'))"`

## Connection check

`python -m src.model` → `OpenAI API connection status: OK`

## Results

| # | Question | Expected | Actual | Result |
|---|----------|----------|--------|--------|
| A | What is customer due diligence? | Grounded answer + sources | Defined CDD (identify/verify customer, beneficial owner, purpose of relationship); 3 sources from BNM AML/CFT/CPF & TFS PD (030-14) | Pass |
| B | Can you explain murabahah in simple words? | Grounded answer + sources | Explained cost-plus-profit sale with disclosed price and instalment repayment; sources: BNM Murabahah PD, Ijarah PD, Mudarabah PD | Pass |
| C | Write me a nasi lemak recipe | Out-of-scope fallback, no OpenAI call | Returned `FALLBACK_MESSAGE` | Pass |
| D | Is my company product officially Shariah-compliant? | Refuse to certify, refer to qualified authority | Declined to certify, summarised general criteria (riba, maysir, gharar, Shariah governance), advised consulting a qualified Shariah scholar or regulator; 3 sources (BNM Shariah Governance PD, Shariah Resolutions, IFSA 2013, IFSB-31) | Pass |
| E | Invalid API key (`sk-wrong-key-for-testing`, set only for that terminal session) | Friendly error, no crash, no key exposed to user | User saw `ERROR_MESSAGE` ("Sorry, the answer service is unavailable right now…"); logged `GenerationError` | Pass |

## Observations

- Retrieval threshold correctly blocks off-topic questions before any API call (C).
- The system prompt prevents official Shariah certification (D).
- In test E the console log showed OpenAI's own masked key text
  (`sk-wrong************ting`). It never reached the user-facing answer, but it
  will be reviewed under KAN-42 (security review).
- The `HF_TOKEN` warning from Hugging Face is harmless (unauthenticated model
  download) and does not affect results.

## KAN-47: Conversation memory and small talk (25 November 2026)

Scripted check of `process_question(question, history)` on branch
`fix/memory-topic`.

- **Retrieval:** real (`all-MiniLM-L6-v2`, TOP_K = 3, THRESHOLD = 0.45).
- **OpenAI:** **not called.** `model.generate_answer` was replaced by a stub
  that records the text it would have been sent. So this check shows which
  path the pipeline takes (small talk, follow-up with history, new question,
  fallback). It does **not** measure the quality of generated answers.
- **Histories used:**
  - *English:* "What is murabahah?" followed by an answer with sources.
  - *Malay:* "Apa itu ijarah?" followed by an answer with sources.
  - *English + small talk:* the English history followed by "oh ok" and its
    small-talk reply.

| # | Message | History | Expected | Actual | Result |
|---|---------|---------|----------|--------|--------|
| C1 | oh ok | English | English small-talk reply, no search | "Glad that helps! 😊 Is there anything else I can help you with? …" | Pass |
| C2 | hm ok | English | Same as C1 (thinking sound ignored) | "Glad that helps! 😊 …" | Pass |
| C3 | hmm | none | English reply with example questions | "No worries, take your time! 😊 You can ask me things like …" | Pass |
| C4 | hmm | Malay | Malay reply | "Tak apa, ambil masa anda! 😊 Kalau ada yang kurang jelas, …" | Pass |
| C5 | tq | Malay | Malay thanks reply | "Sama-sama! 😊 Tanya sahaja jika ada soalan lain." | Pass |
| C6 | terima kasih | English | Malay thanks reply (the phrase itself is Malay) | "Sama-sama! 😊 …" | Pass |
| C7 | bye | English | English goodbye | "Goodbye! 👋 Thanks for using FinWiseIQ. Come back anytime." | Pass |
| C8 | Tell me more | English | Follow-up: search with the topic, send history | Answered with history | Pass |
| C9 | Tell me more | English + small talk | Topic still murabahah ("oh ok" skipped) | Answered with history | Pass |
| C10 | terangkan lagi | Malay | Follow-up in Malay | Answered with history | Pass |
| C11 | How is it different from ijarah? | English | Refers back: search with the topic, send history | Answered with history | Pass |
| C12 | What is takaful? | English | New question: no history sent | Answered, no history | Pass |
| C13 | How do I cook nasi lemak? | English | English fallback, OpenAI not called | English fallback | Pass |
| C14 | mcm mana nak simpan duit | none | Malay fallback, OpenAI not called | Malay fallback | Pass |
| C15 | ok what is ijarah? | English | Not small talk (whole message is not a phrase) | Answered, no history | Pass |

**Result:** 15 / 15 behaved as designed.

**What this check does not show:**

- Answer quality for follow-ups with the real model. During development the
  flow "What is murabahah?" → "oh ok" → "tell me more" was also tried by hand
  in the Gradio app, but those answers were not recorded here.
- Phrases outside the word lists. For example, "hmm ok la tu" is not on any
  list, so it goes through the normal search and usually gets the fallback.
- Malay questions in Malay wording. These often fail retrieval (see README
  Section 12, "Malay retrieval check"), so C14 shows the Malay fallback, not a
  Malay answer.

The automated tests for these cases are in `tests/test_pipeline.py`
(`python -m pytest tests/test_pipeline.py -q`).
