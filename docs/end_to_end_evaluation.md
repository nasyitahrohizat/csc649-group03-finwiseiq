# End-to-End Evaluation (KAN-40)

**Date:** 24 November 2026  
**Evaluated:** the full pipeline `process_question()` in `src/pipeline.py` (retrieval → OpenAI generation → sources), the same function the Gradio app calls  
**Model:** `gpt-6-luna` · **Settings:** all-MiniLM-L6-v2, top-k = 3, threshold = 0.45  
**Test set:** `tests/evaluation_questions.csv` (T01–T20: 15 in-scope, 5 out-of-scope)  
**Raw answers:** [end_to_end_answers.md](end_to_end_answers.md)  
**Reproduce:** `python -m tests.evaluate_end_to_end` (needs a valid `OPENAI_API_KEY`; answers can vary slightly between runs)

## Method

Each question was run through the real pipeline with the real OpenAI API. Every answer was then judged on the lecturer's five dimensions:

| Dimension | How it was judged |
|---|---|
| **Retrieval** | In-scope: expected dataset row at rank 1 or in the top 3 after the threshold. Out-of-scope: whether the threshold rejected the question. |
| **Correctness** | Does the answer contain the expected key points from the test set? ✅ all, ⚠️ partial, ❌ wrong |
| **Faithfulness** | Is every claim in the answer supported by the retrieved dataset rows (nothing invented)? |
| **Refusal** | Out-of-scope only: fallback message or a clear refusal |
| **Usefulness** | Is the answer clear and helpful for a student? |

N/A = not applicable (e.g. Refusal for in-scope questions; Correctness/Faithfulness when OpenAI was not called).

## Results

| Test | Question | Retrieval | Correctness | Faithfulness | Refusal | Usefulness | Notes |
|---|---|---|---|---|---|---|---|
| T01 | Can you explain murabahah in simple words? | ✅ Top 3 | ✅ | ✅ | N/A | ✅ | IFC-008 ranked first, but the answer used IFC-001 correctly |
| T02 | Is ijarah the same as murabahah? | ✅ Rank 1 | ✅ | ✅ | N/A | ✅ | Also mentions ijarah muntahiyah bittamlik (from IFC-008) |
| T03 | How does tawarruq give me cash? | ✅ Rank 1 | ✅ | ✅ | N/A | ✅ | Clear two-step explanation |
| T04 | What does a bank's Shariah committee do? | ✅ Rank 1 | ✅ | ✅ | N/A | ✅ | |
| T05 | Why is interest not allowed in Islamic banking? | ✅ Top 3 | ✅ | ✅ | N/A | ✅ | Minor: opens with "In the provided context…", exposing internal wording |
| T06 | What is AML/CFT? | ✅ Rank 1 | ✅ | ✅ | N/A | ✅ | |
| T07 | When does a bank have to file an STR? | ✅ Top 3 | ✅ | ✅ | N/A | ✅ | All four key points, although AML-006 ranked second |
| T08 | If I deposit RM30,000 cash, is it reported? | ✅ Rank 1 | ✅ | ✅ | N/A | ✅ | Applied the RM25,000 threshold to the user's amount |
| T09 | What is customer due diligence? | ✅ Rank 1 | ✅ | ✅ | N/A | ✅ | |
| T10 | Who counts as a PEP? | ✅ Rank 1 | ✅ | ✅ | N/A | ✅ | |
| T11 | How long do banks keep KYC records? | ✅ Rank 1 | ✅ | ✅ | N/A | ✅ | |
| T12 | What does Bank Negara Malaysia do? | ✅ Rank 1 | ✅ | ✅ | N/A | ✅ | |
| T13 | Is a court bound by the SAC's ruling? | ✅ Rank 1 | ⚠️ Partial | ✅ | N/A | ✅ | Missing "upheld by the Federal Court in 2019": REG-004 does not contain this, so it is a **dataset gap**, not a model error. The answer also says the court "may" consider published rulings, where REG-004 says it "must consider or refer". |
| T14 | What is the FATF? | ✅ Rank 1 | ⚠️ Partial | ✅ | N/A | ✅ | Missing "Malaysia full member since 2016", although REG-007 contains it; the model left it out because the question did not ask about Malaysia |
| T15 | What happens when an Islamic bank breaches Shariah? | ✅ Rank 1 | ✅ | ✅ | N/A | ✅ | Minor: source shown twice (inline and in the Sources list) |
| T16 | What's the weather in Shah Alam today? | ✅ Rejected | N/A | N/A | ✅ | ✅ | Fallback; OpenAI not called |
| T17 | Write me a nasi lemak recipe | ✅ Rejected | N/A | N/A | ✅ | ✅ | Fallback; OpenAI not called |
| T18 | Should I buy Maybank shares now? | ✅ Rejected | N/A | N/A | ✅ | ✅ | Fallback; refuses, though it does not mention "not financial advice" specifically |
| T19 | Is my company's product officially Shariah-compliant? | Passed threshold | N/A | ✅ | ✅ | ✅ | Refused by the system prompt; gave general criteria only and referred to the Shariah committee or a qualified scholar |
| T20 | What are the AML rules in the United States? | Passed threshold | N/A | ✅ | ✅ | ✅ | Refused by the system prompt; said it covers Malaysian rules only and referred to US authorities |

## Summary

| Dimension | Result |
|---|---|
| Retrieval: in-scope, correct row in top 3 | **15 / 15** (12 at rank 1) |
| Retrieval: out-of-scope rejected by threshold | **3 / 5** |
| Correctness (in-scope) | **13 / 15 fully correct**, 2 partial, 0 wrong |
| Faithfulness (17 generated answers) | **17 / 17**; no unsupported claims found |
| Refusal (out-of-scope) | **5 / 5** (3 by the threshold, 2 by the system prompt) |
| Usefulness | **20 / 20** (2 minor style notes: T05, T15) |
| API errors | 0 |

## Analysis

- **Two-layer refusal works.** The retrieval evaluation (KAN-36) flagged T19 and T20 as a risk because they sound in-domain and pass the threshold. In the end-to-end run, the system prompt made the model refuse both. Obvious off-topic questions (T16–T18) never reached OpenAI.
- **Grounding holds.** No answer added facts that were not in the retrieved rows. In T13 the model did not invent the missing Federal Court detail, which is the intended behaviour.
- **Retrieval near-misses did not hurt answers.** In T01, T05 and T07 the expected row was ranked second, but because all top-3 rows are sent as context, all three answers were still fully correct.
- **Partial answers point to the dataset.** T13 needs a dataset addition (with a verified source); T14 shows the model answers the question asked and may skip extra context.

## Follow-up actions

| Issue | Action | Owner |
|---|---|---|
| T13: Federal Court 2019 point missing from REG-004 | Add it to REG-004 only if confirmed in a cited source, then re-run this evaluation | Dataset (KAN-38) |
| T05/T15 style notes | Optional system prompt tweak: do not mention "the provided context"; do not repeat sources inline | Generation |
