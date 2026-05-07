from typing import List, Dict, Any
import uuid
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
except Exception:  # pragma: no cover - optional dependency
    QdrantClient = None
    Distance = VectorParams = PointStruct = None

from core.memory.embedder import Embedder


class VectorStore:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        collection_name: str = "solutions",
    ):
        self.client = QdrantClient(host=host, port=port) if QdrantClient else None
        self.embedder = Embedder()
        self.collection_name = collection_name
        self._memory_points = []
        self._ensure_collection()

    def _ensure_collection(self):
        if not self.client:
            return
        try:
            self.client.get_collection(self.collection_name)
        except:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=384,
                    distance=Distance.COSINE,
                ),
            )

    async def add_solution(
        self,
        task: str,
        code: str,
        score: float,
        reward: float,
        timestamp: str,
    ) -> str:
        solution_id = str(uuid.uuid4())
        embedding = self.embedder.embed(task)

        if not self.client:
            self._memory_points.append(
                {
                    "id": solution_id,
                    "vector": embedding,
                    "payload": {
                        "task": task,
                        "code": code,
                        "score": score,
                        "reward": reward,
                        "timestamp": timestamp,
                        "solution_id": solution_id,
                    },
                }
            )
            return solution_id

        point = PointStruct(
            id=hash(solution_id) % (2**31),
            vector=embedding,
            payload={
                "task": task,
                "code": code,
                "score": score,
                "reward": reward,
                "timestamp": timestamp,
                "solution_id": solution_id,
            },
        )

        self.client.upsert(
            collection_name=self.collection_name,
            points=[point],
        )
        return solution_id

    async def search(
        self,
        query: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        query_embedding = self.embedder.embed(query)

        if not self.client:
            scored = []
            for point in self._memory_points:
                sim = self.embedder.similarity(query_embedding, point["vector"])
                payload = point["payload"]
                scored.append(
                    {
                        "task": payload["task"],
                        "code": payload["code"],
                        "score": payload["score"],
                        "reward": payload["reward"],
                        "similarity": sim,
                    }
                )
            return sorted(scored, key=lambda item: item["similarity"], reverse=True)[:limit]

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=limit,
        )

        return [
            {
                "task": point.payload["task"],
                "code": point.payload["code"],
                "score": point.payload["score"],
                "reward": point.payload["reward"],
                "similarity": point.score,
            }
            for point in results
        ]

    async def search_by_score(self, min_score: float = 0.9) -> List[Dict[str, Any]]:
        if not self.client:
            return [
                point["payload"]
                for point in self._memory_points
                if point["payload"].get("score", 0) >= min_score
            ]

        results = self.client.scroll(
            collection_name=self.collection_name,
            limit=100,
        )

        high_performers = []
        for point in results[0]:
            if point.payload.get("score", 0) >= min_score:
                high_performers.append(point.payload)

        return high_performers

    async def get_statistics(self) -> Dict[str, Any]:
        if not self.client:
            scores = [p["payload"].get("score", 0) for p in self._memory_points]
            rewards = [p["payload"].get("reward", 0) for p in self._memory_points]
            return {
                "total_solutions": len(scores),
                "avg_score": sum(scores) / len(scores) if scores else 0.0,
                "max_score": max(scores) if scores else 0.0,
                "avg_reward": sum(rewards) / len(rewards) if rewards else 0.0,
            }

        info = self.client.get_collection(self.collection_name)
        
        results = self.client.scroll(
            collection_name=self.collection_name,
            limit=1000,
        )

        scores = [p.payload.get("score", 0) for p in results[0]]
        rewards = [p.payload.get("reward", 0) for p in results[0]]

        return {
            "total_solutions": len(scores),
            "avg_score": sum(scores) / len(scores) if scores else 0.0,
            "max_score": max(scores) if scores else 0.0,
            "avg_reward": sum(rewards) / len(rewards) if rewards else 0.0,
        }
