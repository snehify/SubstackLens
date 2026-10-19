from threading import Lock

import numpy as np

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_model = None
_cache_signature = None
_cache_embeddings = None
_model_lock = Lock()


def get_document_text(post: dict) -> str:
    """Build searchable text from an indexed article."""
    fields = [
        ("Title", post.get("title")),
        ("Publication", post.get("publication")),
        ("Author", post.get("author")),
        ("Summary", post.get("summary")),
    ]

    parts = [
        f"{label}: {value.strip()}"
        for label, value in fields
        if value and str(value).strip()
    ]

    return "\n".join(parts) or str(post.get("url", ""))


def semantic_rank(posts: list[dict], query: str) -> list[dict]:
    """Rank articles by semantic similarity to the query."""
    global _model, _cache_signature, _cache_embeddings

    if not posts:
        return []

    texts = [get_document_text(post) for post in posts]

    # Include article content in the signature so ingestion updates
    # invalidate the cached embeddings automatically.
    signature = tuple(
        (
            post.get("id"),
            post.get("url"),
            post.get("title"),
            post.get("author"),
            post.get("publication"),
            post.get("summary"),
            post.get("published"),
        )
        for post in posts
    )

    with _model_lock:
        # Load the model only once per backend process.
        if _model is None:
            from sentence_transformers import SentenceTransformer

            _model = SentenceTransformer(MODEL_NAME, device="cpu")

        # Reuse article embeddings until the indexed content changes.
        if signature != _cache_signature:
            _cache_embeddings = _model.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            _cache_signature = signature

        query_embedding = _model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )[0]

        # Normalized vectors can be compared with their dot product.
        scores = _cache_embeddings @ query_embedding

    ranked = sorted(
        zip(posts, scores.tolist()),
        key=lambda item: item[1],
        reverse=True,
    )

    return [
        {
            **post,
            "semantic_score": round(float(score), 4),
        }
        for post, score in ranked
    ]