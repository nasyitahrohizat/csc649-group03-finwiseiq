"""FinWiseIQ retrieval: load the Q&A CSV, embed it, and find the top matches."""
from functools import lru_cache
from pathlib import Path

import pandas as pd
from sentence_transformers import SentenceTransformer

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "finwiseiq_dataset.csv"
MODEL_NAME = "all-MiniLM-L6-v2"
TOP_K = 3
THRESHOLD = 0.45  # calibrated on tests/evaluation_questions.csv (16 Nov)
COLUMNS = ["id", "category", "question", "answer",
           "source", "source_section", "last_reviewed"]


def load_dataset(path: Path = DATA_PATH) -> pd.DataFrame:
    """Read the CSV, check the columns, and drop empty rows."""
    df = pd.read_csv(path)
    missing = [c for c in COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"CSV is missing columns: {missing}")
    df = df.dropna(subset=["question", "answer"])
    df["question"] = df["question"].str.strip()
    df["answer"] = df["answer"].str.strip()
    df = df[(df["question"] != "") & (df["answer"] != "")]
    return df.reset_index(drop=True)
    
@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    """Load the embedding model once and reuse it."""
    return SentenceTransformer(MODEL_NAME)


@lru_cache(maxsize=1)
def get_index():
    """Embed every dataset question once. Returns (dataframe, embeddings)."""
    df = load_dataset()
    embeddings = get_model().encode(df["question"].tolist(),
                                    normalize_embeddings=True)
    return df, embeddings


def retrieve_context(question: str) -> list[dict]:
    """Return up to TOP_K matches (best first) scoring >= THRESHOLD.
    Returns [] when the question is empty or nothing is relevant."""
    if not question or not question.strip():
        return []
    df, embeddings = get_index()
    q = get_model().encode([question.strip()], normalize_embeddings=True)[0]
    scores = embeddings @ q  # cosine similarity (vectors are normalised)
    results = []
    for i in scores.argsort()[::-1][:TOP_K]:
        score = float(scores[i])
        if score < THRESHOLD:
            break
        row = df.iloc[i]
        results.append({
            "id": row["id"], "category": row["category"],
            "question": row["question"], "answer": row["answer"],
            "source": row["source"], "source_section": row["source_section"],
            "score": round(score, 4),
        })
    return results
