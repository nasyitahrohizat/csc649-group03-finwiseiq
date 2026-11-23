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
