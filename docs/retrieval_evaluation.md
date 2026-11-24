# Retrieval Evaluation (KAN-36)

**Date:** 16 November 2026 (re-run 24 November 2026 after the KAN-38 dataset update)  
**Evaluated:** `retrieve_context()` in `src/retrieval.py`  
**Dataset:** `data/finwiseiq_dataset.csv` (55 Q&A pairs after KAN-38; 50 at the first run)  
**Test set:** `tests/evaluation_questions.csv` (15 in-scope, 5 out-of-scope)  
**Settings:** all-MiniLM-L6-v2 embeddings, cosine similarity, top-k = 3, threshold = 0.45  
**Reproduce:** `python -m tests.evaluate_retrieval`

## Method

Each evaluation question is worded differently from the dataset questions, to test
semantic matching rather than keyword matching. For in-scope questions we check whether
the expected dataset row is returned at rank 1 or anywhere in the top 3 (after the
threshold). For out-of-scope questions we check whether the threshold rejects them
(an empty result, so OpenAI is not called).

## Summary

| Metric                              | Result         |
| ----------------------------------- | -------------- |
| In-scope: correct row at rank 1     | 12 / 15 (80%)  |
| In-scope: correct row in top 3      | 15 / 15 (100%) |
| Out-of-scope: rejected by threshold | 3 / 5          |

## Results

Re-run on 24 November 2026 after the KAN-38 dataset update (55 rows). Rank-1 and top-3
results are unchanged from the 16 November run.

| Test | Type | Question | Expected | Top 3 (score) | Result |
|---|---|---|---|---|---|
| T01 | in_scope | Can you explain murabahah in simple words? | IFC-001 | IFC-008 (0.710), IFC-001 (0.622), IFC-010 (0.586) | Top 3 |
| T02 | in_scope | Is ijarah the same as murabahah? | IFC-008 | IFC-008 (0.933), IFC-007 (0.758), IFC-001 (0.561) | Rank 1 |
| T03 | in_scope | How does tawarruq give me cash? | IFC-005 | IFC-005 (0.670), IFC-006 (0.577), IFC-001 (0.397) | Rank 1 |
| T04 | in_scope | What does a bank's Shariah committee do? | IFF-006 | IFF-006 (0.829), IFF-009 (0.775), IFF-005 (0.766) | Rank 1 |
| T05 | in_scope | Why is interest not allowed in Islamic banking? | IFF-002 | IFF-011 (0.699), IFF-005 (0.652), IFF-002 (0.649) | Top 3 |
| T06 | in_scope | What is AML/CFT? | AML-001 | AML-001 (0.840), AML-005 (0.667), AML-004 (0.629) | Rank 1 |
| T07 | in_scope | When does a bank have to file an STR? | AML-006 | KYC-002 (0.553), AML-006 (0.495), AML-007 (0.477) | Top 3 |
| T08 | in_scope | If I deposit RM30,000 cash, is it reported? | AML-007 | AML-007 (0.523), AML-012 (0.443), AML-006 (0.369) | Rank 1 |
| T09 | in_scope | What is customer due diligence? | KYC-001 | KYC-001 (0.860), KYC-009 (0.686), KYC-006 (0.481) | Rank 1 |
| T10 | in_scope | Who counts as a PEP? | KYC-007 | KYC-007 (0.600), KYC-008 (0.520), AML-001 (0.228) | Rank 1 |
| T11 | in_scope | How long do banks keep KYC records? | AML-009 | AML-009 (0.609), KYC-002 (0.484), KYC-003 (0.428) | Rank 1 |
| T12 | in_scope | What does Bank Negara Malaysia do? | REG-001 | REG-001 (0.952), REG-009 (0.754), REG-003 (0.728) | Rank 1 |
| T13 | in_scope | Is a court bound by the SAC's ruling? | REG-004 | REG-004 (0.888), KYC-002 (0.278), IFC-006 (0.267) | Rank 1 |
| T14 | in_scope | What is the FATF? | REG-007 | REG-007 (0.608), AML-001 (0.333), REG-006 (0.301) | Rank 1 |
| T15 | in_scope | What happens when an Islamic bank breaches Shariah? | REG-010 | REG-010 (0.766), IFF-005 (0.702), IFF-009 (0.697) | Rank 1 |
| T16 | out_of_scope | What's the weather in Shah Alam today? | - | IFF-012 (0.300), IFC-007 (0.278), IFC-005 (0.259) | Rejected |
| T17 | out_of_scope | Write me a nasi lemak recipe | - | IFC-011 (0.409), IFC-007 (0.302), IFC-010 (0.251) | Rejected |
| T18 | out_of_scope | Should I buy Maybank shares now? | - | IFC-002 (0.388), IFF-004 (0.277), REG-009 (0.270) | Rejected |
| T19 | out_of_scope | Is my company's product officially Shariah-compliant? | - | IFF-001 (0.630), IFF-008 (0.628), REG-010 (0.468) | Passed threshold |
| T20 | out_of_scope | What are the AML rules in the United States? | - | REG-005 (0.561), AML-005 (0.529), AML-001 (0.512) | Passed threshold |

Scores below 0.45 are shown for reference only; `retrieve_context()` drops them, so they
are not sent to OpenAI.

## Analysis

- **Top-3 accuracy is 100%.** All three matches are passed to OpenAI as context, so the
  correct information reached the model for every in-scope question.
- **Three rank-1 near-misses:**
  - T01 "Can you explain murabahah in simple words?" ranked IFC-008 ("difference between
    Ijarah and Murabahah") first, because it also mentions murabahah. The expected IFC-001
    was second.
  - T05 "Why is interest not allowed…?" scored IFF-005 (0.652) and the expected IFF-002
    (0.649) almost equally. After KAN-38 the new row IFF-011 ("difference between Islamic
    and conventional banking", 0.699) ranks first; it also explains riba, so the context
    is still correct.
  - T07 "When does a bank have to file an STR?" ranked KYC-002 ("When must a bank carry
    out CDD?") first, because both ask _when must a bank…_. The expected AML-006 was second.
- **Threshold choice (0.45):** clear off-topic questions (weather, recipe, stock tip)
  scored at most 0.388 in the first run and were rejected. The lowest correct match kept
  was AML-006 at 0.495, which a 0.5 threshold would have dropped.
- **Re-check after KAN-38:** the new sukuk row IFC-011 raised the nasi lemak recipe
  question (T17) to 0.409. It is still rejected, and 0.45 still sits between the highest
  score among the clearly off-topic questions T16–T18 (0.409) and the lowest correct
  match (0.495), so the threshold is unchanged. (T19 and T20 are out of scope but sound
  in-domain; they score 0.630 and 0.561 and pass the threshold, see the limitation below.) The margin on the off-topic side is now smaller (0.041 instead of 0.062),
  so the threshold should be re-checked whenever rows are added.
- **Limitation:** T19 (Shariah certification) and T20 (US AML rules) sound in-domain, so
  they pass the threshold (0.630 and 0.561). Retrieval alone cannot reject them; the
  system prompt must make the model refuse or state its scope. This is checked in KAN-37.
