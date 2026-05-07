from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import json
import redis
from datetime import datetime


class EvaluationMetric(Enum):
    SUCCESS_RATE = "success_rate"
    LATENCY = "latency"
    COST = "cost"
    QUALITY = "quality"
    EFFICIENCY = "efficiency"


@dataclass
class EvaluationResult:
    metric: EvaluationMetric
    value: float
    timestamp: str
    task_id: str


class EvaluationSystem:
    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379):
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            decode_responses=True,
        )
        self.metrics: Dict[str, List[float]] = {}

    async def evaluate(
        self,
        task_id: str,
        code: str,
        test_score: float,
        latency: float,
        quality_metrics: Dict[str, float],
    ) -> Dict[str, float]:
        scores = {
            "success_rate": test_score,
            "latency_efficiency": 1.0 / (1.0 + latency),
            "code_quality": quality_metrics.get("complexity", 0.5),
            "documentation": 1.0 if quality_metrics.get("has_docstring") else 0.5,
            "test_coverage": quality_metrics.get("test_coverage", 0.5),
        }
        
        overall_score = sum(scores.values()) / len(scores)
        
        await self._store_evaluation(task_id, scores, overall_score)
        
        return scores

    async def _store_evaluation(
        self,
        task_id: str,
        scores: Dict[str, float],
        overall: float,
    ) -> None:
        evaluation = {
            "task_id": task_id,
            "scores": scores,
            "overall": overall,
            "timestamp": datetime.now().isoformat(),
        }
        
        self.redis_client.lpush(
            "evaluations",
            json.dumps(evaluation),
        )

    async def get_benchmark_results(
        self,
        task_type: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        evaluations = self.redis_client.lrange("evaluations", 0, limit - 1)
        return [json.loads(e) for e in evaluations]

    async def get_statistics(self) -> Dict[str, float]:
        evaluations = self.redis_client.lrange("evaluations", 0, 1000)
        results = [json.loads(e) for e in evaluations]
        
        if not results:
            return {}
        
        overall_scores = [r["overall"] for r in results]
        return {
            "avg_score": sum(overall_scores) / len(overall_scores),
            "max_score": max(overall_scores),
            "min_score": min(overall_scores),
            "total_evaluations": len(overall_scores),
        }
