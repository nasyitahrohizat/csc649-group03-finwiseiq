"""Tests for src/retrieval.py (KAN-19).

How pytest works:
- pytest looks in the tests/ folder (set in pytest.ini) for files named
  test_*.py and runs every function whose name starts with test_.
- `assert <condition>` means "this must be true". If it is false, the test
  FAILS and pytest shows the line and the actual value.
- GitHub runs these tests on every pull request (the green "tests" check),
  so if anyone breaks retrieval later, the PR cannot be merged.

Run locally with:  pytest -v
"""
import pytest

# Works because pytest.ini has "pythonpath = ." (repo root is importable).
from src.retrieval import load_dataset, retrieve_context


def test_dataset_loads_with_all_columns():
    # Test 1: the real dataset loads properly.
    # Loads data/finwiseiq_dataset.csv and checks it is not empty and has
    # the important columns. Catches a deleted, moved or broken dataset file.
    df = load_dataset()
    assert not df.empty
    assert "question" in df.columns and "source" in df.columns


def test_missing_column_raises(tmp_path):
    # Test 2: a broken CSV gives a clear error.
    # tmp_path = a temporary folder pytest creates for this test and deletes
    # afterwards, so our real project files are never touched.
    # We write a fake CSV with only 2 columns (id, question), missing the
    # other 5 agreed columns.
    bad = tmp_path / "bad.csv"
    bad.write_text("id,question\n1,hi\n", encoding="utf-8")
    # pytest.raises(ValueError) = the code inside MUST raise a ValueError.
    # Proves the column check in load_dataset() works: a broken CSV stops
    # immediately with a clear message instead of failing confusingly later.
    with pytest.raises(ValueError):
        load_dataset(bad)


def test_relevant_question_returns_sorted_matches():
    # Test 3 (most important): a real question finds the right answer.
    results = retrieve_context("What is customer due diligence?")
    # (a) Between 1 and 3 results: TOP_K=3 is respected and the question
    #     is not wrongly rejected by the threshold.
    assert 1 <= len(results) <= 3
    # (b) The best match (results[0]) is KYC-001, the correct dataset row.
    #     Proves the semantic search works.
    assert results[0]["id"] == "KYC-001"
    # (c) Scores are sorted highest -> lowest (best first).
    #     Collect the scores into a list, e.g. [0.86, 0.686, 0.481];
    #     if it equals the same list sorted in descending order,
    #     the results were already best first.
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_off_topic_question_returns_empty():
    # Test 4: an off-topic question returns nothing.
    # Proves the THRESHOLD (0.45) works: an unrelated question gets [],
    # so process_question() shows the fallback and OpenAI is never called.
    assert retrieve_context("What is the best pizza in Kuala Lumpur?") == []


def test_empty_question_returns_empty():
    # Test 5: a blank question is handled safely.
    # "   " is what a user sends if they press Enter by accident.
    # Proves the `if not question.strip(): return []` line works and the
    # code does not crash.
    assert retrieve_context("   ") == []
