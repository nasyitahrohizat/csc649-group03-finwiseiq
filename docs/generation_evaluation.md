# OpenAI Answer Quality Evaluation (KAN-37)

**Date:** 24 November 2026  
**Evaluated:** `generate_answer()` in `src/model.py` + `SYSTEM_PROMPT` in `src/prompt.py` (with `format_context()` in `src/pipeline.py`)  
**Model:** `gpt-6-luna`  
**Test set:** `tests/evaluation_questions.csv` (T01–T20: 15 in-scope, 5 out-of-scope)  
**Raw answers:** [generation_evaluation_answers.md](generation_evaluation_answers.md)  
**Reproduce:** `python -m tests.evaluate_generation` (requires a valid `OPENAI_API_KEY`)

## Objective & Method

Unlike end-to-end evaluation (`KAN-40`), this evaluation isolates **OpenAI generation quality** (`src/model.py` + `src/prompt.py`):

- **In-scope (`T01–T15`):** Ground-truth dataset row plus top retrieved context rows formatted via `format_context()` were supplied to `generate_answer()`.
- **Out-of-scope (`T16–T20`):** Tangential/unrelated dataset rows were deliberately passed to `generate_answer()` (bypassing the retrieval threshold) to verify that `SYSTEM_PROMPT` enforces safe boundaries even when OpenAI is invoked directly.

| Dimension | Criteria |
|---|---|
| **Correctness** | Covers expected key points (`✅` complete, `⚠️` partial, `❌` incorrect) |
| **Faithfulness** | Strictly grounded in supplied context with zero hallucinated facts |
| **Refusal** | Out-of-scope: clearly refuses off-topic, advisory, Shariah certification, or foreign-law queries |
| **Usefulness** | Clear, well-structured, and helpful for students |

## Results

| Test | Question | Correctness | Faithfulness | Refusal | Usefulness | Notes |
|---|---|---|---|---|---|---|
| T01 | Can you explain murabahah in simple words? | ✅ | ✅ | N/A | ✅ | Explains cost-plus-profit disclosure and instalment payment clearly |
| T02 | Is ijarah the same as murabahah? | ✅ | ✅ | N/A | ✅ | Clearly contrasts lease (bank retains ownership) vs. sale |
| T03 | How does tawarruq give me cash? | ✅ | ✅ | N/A | ✅ | Clean numbered two-step sale explanation |
| T04 | What does a bank's Shariah committee do? | ✅ | ✅ | N/A | ✅ | Covers SAC advice, non-compliance affirmation, rectification endorsement, and board escalation |
| T05 | Why is interest not allowed in Islamic banking? | ✅ | ✅ | N/A | ✅ | Explains *riba* prohibition and trade/lease/partnership alternatives |
| T06 | What is AML/CFT? | ✅ | ✅ | N/A | ✅ | Accurate definition of AML/CFT measures |
| T07 | When does a bank have to file an STR? | ✅ | ✅ | N/A | ✅ | Includes suspicion regardless of amount, attempted transactions, next working day, and BNM FIED |
| T08 | If I deposit RM30,000 cash, is it reported? | ✅ | ✅ | N/A | ✅ | Correctly applies RM25,000 daily CTR threshold and 5-working-day filing rule |
| T09 | What is customer due diligence? | ✅ | ✅ | N/A | ✅ | Covers customer verification, beneficial owner identification, and relationship purpose |
| T10 | Who counts as a PEP? | ✅ | ✅ | N/A | ✅ | Covers prominent public functions, foreign/domestic/international PEPs, family and close associates |
| T11 | How long do banks keep KYC records? | ✅ | ✅ | N/A | ✅ | States at least 6 years and longer if under investigation/prosecution |
| T12 | What does Bank Negara Malaysia do? | ✅ | ✅ | N/A | ✅ | Covers central bank mandate, monetary/financial stability, supervision, AML/CFT, and SAC |
| T13 | Is a court bound by the SAC's ruling? | ⚠️ Partial | ✅ | N/A | ✅ | Correctly states court must consider/refer and is bound; omits 2019 Federal Court detail (`REG-004` dataset gap, not hallucination) |
| T14 | What is the FATF? | ⚠️ Partial | ✅ | N/A | ✅ | Covers 40 Recommendations and mutual evaluations; omits Malaysia 2016 membership detail as question asked generally |
| T15 | What happens when an Islamic bank breaches Shariah? | ✅ | ✅ | N/A | ✅ | Covers board/Shariah committee reporting, rectification endorsement, BNM notification, and IFSA s.28(3) plan |
| T16 | What's the weather in Shah Alam today? | N/A | ✅ | ✅ | ✅ | Polite refusal; directs user to a weather service |
| T17 | Write me a nasi lemak recipe | N/A | ✅ | ✅ | ✅ | Polite refusal; reiterates Islamic finance & Malaysian compliance scope |
| T18 | Should I buy Maybank shares now? | N/A | ✅ | ✅ | ✅ | Refuses investment advice and Shariah stock screening; refers to licensed adviser/scholar |
| T19 | Is my company's product officially Shariah-compliant? | N/A | ✅ | ✅ | ✅ | Refuses formal Shariah certification; gives general principles and refers to Shariah committee/scholar |
| T20 | What are the AML rules in the United States? | N/A | ✅ | ✅ | ✅ | Refuses foreign jurisdiction rules without guessing; offers Malaysian AMLA context instead |

## Summary

| Metric | Score |
|---|---|
| **Correctness (in-scope)** | **13 / 15 fully correct**, 2 partial (`T13` dataset gap, `T14` concise scope), 0 incorrect |
| **Faithfulness (all 20 calls)** | **20 / 20 (100%)** — zero unsupported or fabricated claims |
| **Out-of-scope refusal (`T16–T20`)** | **5 / 5 (100%)** — `SYSTEM_PROMPT` prevented all off-topic/advisory/certification leakage |
| **Usefulness & clarity** | **20 / 20 (100%)** |
| **API / runtime errors** | **0 / 20** |

## Key Findings

1. **Strong Context Grounding:** Across all 20 runs with `gpt-6-luna`, the model never invented external facts. In `T13`, where `REG-004` lacks the 2019 Federal Court citation, the model stayed strictly within the supplied text rather than hallucinating.
2. **Robust System Prompt Guardrails:** Even when irrelevant dataset rows were deliberately passed to `generate_answer()` for `T16–T20`, the model consistently declined out-of-scope requests, investment advice (`T18`), formal Shariah certification (`T19`), and foreign legal advice (`T20`).
3. **Security Hardening Verified (`KAN-42`):** Automated unit tests (`pytest tests/test_model.py -v`, 12 passed) confirm `AuthenticationError` logs a generic message (`OpenAI authentication failed.`) without exposing raw exception text or API keys.
