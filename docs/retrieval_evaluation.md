# Retrieval Evaluation (KAN-36)

**Date:** 16 November 2026  
**Evaluated:** `retrieve_context()` in `src/retrieval.py`  
**Dataset:** `data/finwiseiq_dataset.csv` (50 Q&A pairs, 10 per category)  
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

<!-- paste the table from the script output here -->

## Analysis

- **Top-3 accuracy is 100%.** All three matches are passed to OpenAI as context, so the
  correct information reached the model for every in-scope question.
- **Three rank-1 near-misses:**
  - T01 "Can you explain murabahah in simple words?" ranked IFC-008 ("difference between
    Ijarah and Murabahah") first, because it also mentions murabahah. The expected IFC-001
    was second.
  - T05 "Why is interest not allowed…?" scored IFF-005 (0.652) and the expected IFF-002
    (0.649) almost equally.
  - T07 "When does a bank have to file an STR?" ranked KYC-002 ("When must a bank carry
    out CDD?") first, because both ask _when must a bank…_. The expected AML-006 was second.
- **Threshold choice (0.45):** clear off-topic questions (weather, recipe, stock tip)
  scored at most 0.388 and were rejected. The lowest correct match kept was AML-006 at
  0.495, which a 0.5 threshold would have dropped.
- **Limitation:** T19 (Shariah certification) and T20 (US AML rules) sound in-domain, so
  they pass the threshold (0.630 and 0.561). Retrieval alone cannot reject them; the
  system prompt must make the model refuse or state its scope. This is checked in KAN-37.
