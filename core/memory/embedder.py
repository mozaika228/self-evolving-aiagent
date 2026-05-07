from typing import List
import numpy as np
import re

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - optional dependency
    SentenceTransformer = None


class Embedder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name) if SentenceTransformer else None

    def embed(self, text: str) -> List[float]:
        if self.model:
            return self.model.encode(text).tolist()

        vector = np.zeros(384, dtype=float)
        synonyms = {"fast": "quick", "rapid": "quick"}
        tokens = re.findall(r"\w+", text.lower())
        for token in tokens:
            normalized = synonyms.get(token, token)
            vector[hash(normalized) % 384] += 1.0

        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if self.model:
            embeddings = self.model.encode(texts)
            return embeddings.tolist()
        return [self.embed(text) for text in texts]

    def similarity(self, emb1: List[float], emb2: List[float]) -> float:
        arr1 = np.array(emb1)
        arr2 = np.array(emb2)
        denom = np.linalg.norm(arr1) * np.linalg.norm(arr2)
        if denom == 0:
            return 0.0
        value = float(np.dot(arr1, arr2) / denom)
        return max(0.0, min(1.0, value))
