from __future__ import annotations

from dataclasses import dataclass

import faiss
import numpy as np


@dataclass(frozen=True)
class SearchHit:
    index: int
    score: float


class CosineFaissIndex:
    """Exact cosine search using normalized vectors and IndexFlatIP."""

    def __init__(self, dimension: int) -> None:
        self.index = faiss.IndexFlatIP(dimension)

    def add(self, vectors: np.ndarray) -> None:
        if vectors.dtype != np.float32:
            vectors = vectors.astype("float32")
        faiss.normalize_L2(vectors)
        self.index.add(vectors)

    def search(self, query: np.ndarray, top_k: int) -> list[SearchHit]:
        query = query.astype("float32").copy()
        faiss.normalize_L2(query)
        scores, indices = self.index.search(query, min(top_k, self.index.ntotal))
        return [
            SearchHit(int(idx), float(score))
            for idx, score in zip(indices[0], scores[0], strict=True) if idx >= 0
        ]
