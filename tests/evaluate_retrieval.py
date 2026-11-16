"""Retrieval evaluation for FinWiseIQ (KAN-36).

Runs every question in tests/evaluation_questions.csv through the
retriever and prints a Markdown results table plus summary metrics.

Run from the repo root:  python -m tests.evaluate_retrieval
"""
from pathlib import Path

import pandas as pd

from src.retrieval import THRESHOLD, TOP_K, get_index, get_model, retrieve_context

EVAL_PATH = Path(__file__).resolve().parent / "evaluation_questions.csv"


def top_matches(question: str) -> list[tuple[str, float]]:
    """Top-K (id, score) pairs BEFORE the threshold is applied."""
    df, embeddings = get_index()
    q = get_model().encode([question], normalize_embeddings=True)[0]
    scores = embeddings @ q
    return [(df["id"][i], float(scores[i])) for i in scores.argsort()[::-1][:TOP_K]]


def main() -> None:
    ev = pd.read_csv(EVAL_PATH, dtype=str)
    rows = []
    hit1 = hit3 = in_n = rejected = out_n = 0
    for _, t in ev.iterrows():
        top = top_matches(t["question"])
        kept = [r["id"] for r in retrieve_context(t["question"])]
        if t["type"] == "in_scope":
            in_n += 1
            exp = t["expected_dataset_id"]
            if kept[:1] == [exp]:
                hit1 += 1
                result = "Rank 1"
            elif exp in kept:
                hit3 += 1
                result = "Top 3"
            else:
                result = "Miss"
        else:
            out_n += 1
            exp = "-"
            if not kept:
                rejected += 1
                result = "Rejected"
            else:
                result = "Passed threshold"
        top_txt = ", ".join(f"{i} ({s:.3f})" for i, s in top)
        rows.append(f"| {t['test_id']} | {t['type']} | {t['question']} | {exp} | {top_txt} | {result} |")

    print(f"Threshold = {THRESHOLD}, top-k = {TOP_K}\n")
    print("| Test | Type | Question | Expected | Top 3 (score) | Result |")
    print("|---|---|---|---|---|---|")
    print("\n".join(rows))
    print(f"\nIn-scope at rank 1: {hit1}/{in_n}")
    print(f"In-scope in top 3:  {hit1 + hit3}/{in_n}")
    print(f"Out-of-scope rejected by threshold: {rejected}/{out_n}")


if __name__ == "__main__":
    main()
