# KAN-24: Independent OpenAI Generation Test Results

Date: 17 November 2026

## Objective
Verify that `src/model.py` (`generate_answer`) works independently with `src/prompt.py` (`SYSTEM_PROMPT`) using sample CSV-formatted context before connecting to the retrieval module.

## Automated Unit Tests (Mocked API)
Command: `pytest tests/test_model.py -v`
Result: **12 passed in 0.87s** (no live OpenAI API calls made).

Covered test cases:
- Successful context-grounded generation with system prompt injection
- Missing or whitespace-only question / context validation (`ValueError`)
- API error handling (`APITimeoutError`, `AuthenticationError`, `RateLimitError`, `NotFoundError`, `APIConnectionError`, `OpenAIError`)
- API key redaction in logs (`[REDACTED]`) and safe user-facing `GenerationError` messages
- Empty/blank completion response validation
- CSV-formatted sample context tests for relevant, insufficient-context, and out-of-scope queries

## Manual Live API Test Results
Sample context used (formatted from `data/finwiseiq_dataset.csv` entries `IFF-001` and `IFF-002`):
- `[1] ID: IFF-001 | Category: Islamic Finance Fundamentals | Q: What does Shariah-compliant mean in finance? ...`
- `[2] ID: IFF-002 | Category: Islamic Finance Fundamentals | Q: What is riba and why do Islamic banks avoid it? ...`

### 1. Relevant Question
- **Question:** What does Shariah-compliant mean in finance, and what contracts do Islamic banks use instead of riba?
- **Generated Answer:** Accurately synthesized both retrieved passages, explaining avoidance of *riba* (interest), *maysir* (gambling), and *gharar* (speculation/uncertainty), Shariah governance approval, and alternative contracts (*murabahah*, *ijarah*, *musyarakah*, *mudarabah*).
- **Quality Assessment:** Pass — grounded strictly in supplied context, clear formatting, no hallucinated details.

### 2. Insufficient Context
- **Question:** What is the minimum capital requirement for a digital Islamic bank license in Malaysia?
- **Generated Answer:** Stated clearly that the minimum capital requirement is not stated in FinWiseIQ's verified knowledge base, declined to fabricate a figure, and advised checking with Bank Negara Malaysia.
- **Quality Assessment:** Pass — properly refused unsupported regulatory figures and directed user to the official regulator.

### 3. Out-of-Scope Question
- **Question:** Which Bursa Malaysia stock should I buy tomorrow to make quick profit?
- **Generated Answer:** Politely declined to recommend stocks or predict profits, noting that personalized investment advice and live Bursa Malaysia market data are outside FinWiseIQ's verified knowledge base, and recommended consulting a qualified financial planner.
- **Quality Assessment:** Pass — respected educational/non-advisory boundaries in `SYSTEM_PROMPT`.

## Issues Found & Resolved
- **Issue:** Initial live API call returned `Error code: 400 - Unsupported value: 'temperature' does not support 0.2 with this model. Only the default (1) value is supported.`
- **Resolution:** Removed the hardcoded `temperature=0.2` argument in `src/model.py` so `generate_answer()` remains compatible across standard and reasoning OpenAI models. Re-ran `pytest tests/test_model.py -v` (12 passed) and confirmed all 3 live manual test cases succeeded.
