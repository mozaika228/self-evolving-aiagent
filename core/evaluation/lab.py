from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional
import json
import os


@dataclass
class EvalTask:
    task_id: str
    difficulty: str
    prompt: str
    expected_capability: str
    weight: float


@dataclass
class EvalResult:
    task_id: str
    success: bool
    latency_sec: float
    tokens_used: int
    quality_score: float
    novelty_score: float
    retained: bool
    adaptation_iterations: int


class EvaluationLab:
    """Evaluation Lab: suite, A/B baselines, KPI metrics, regression gates."""

    def __init__(self, state_path: str = "core/evaluation/lab_state.json"):
        self.state_path = state_path
        self.tasks = self._default_tasks()
        self.baselines = self._default_baselines()

    def _default_tasks(self) -> List[EvalTask]:
        return [
            EvalTask("s1", "simple", "Add two numbers function", "basic_codegen", 1.0),
            EvalTask("s2", "simple", "Fix failing test quickly", "debugging", 1.0),
            EvalTask("m1", "medium", "Refactor to modular design", "refactoring", 1.2),
            EvalTask("m2", "medium", "Add retries and graceful errors", "robustness", 1.2),
            EvalTask("h1", "hard", "Build autonomous repair loop", "autonomy", 1.6),
            EvalTask("h2", "hard", "Optimize quality under budget", "meta_optimization", 1.6),
        ]

    def _default_baselines(self) -> Dict[str, Dict[str, float]]:
        return {
            "reactive_baseline": {
                "success_rate": 0.62,
                "latency": 4.6,
                "cost": 0.58,
                "novelty": 0.37,
                "retention": 0.41,
                "adaptation_speed": 0.33,
            },
            "memory_baseline": {
                "success_rate": 0.71,
                "latency": 4.1,
                "cost": 0.64,
                "novelty": 0.43,
                "retention": 0.57,
                "adaptation_speed": 0.49,
            },
        }

    def evaluate_candidate(self, candidate_results: List[EvalResult]) -> Dict[str, float]:
        if not candidate_results:
            return {
                "success_rate": 0.0,
                "latency": 999.0,
                "cost": 0.0,
                "novelty": 0.0,
                "retention": 0.0,
                "adaptation_speed": 0.0,
            }

        weights = {task.task_id: task.weight for task in self.tasks}
        total_weight = sum(weights.get(r.task_id, 1.0) for r in candidate_results)

        success_weighted = sum((1.0 if r.success else 0.0) * weights.get(r.task_id, 1.0) for r in candidate_results)
        latency_weighted = sum(r.latency_sec * weights.get(r.task_id, 1.0) for r in candidate_results)
        quality_weighted = sum(r.quality_score * weights.get(r.task_id, 1.0) for r in candidate_results)
        novelty_weighted = sum(r.novelty_score * weights.get(r.task_id, 1.0) for r in candidate_results)
        retention_weighted = sum((1.0 if r.retained else 0.0) * weights.get(r.task_id, 1.0) for r in candidate_results)
        adapt_weighted = sum((1.0 / max(1, r.adaptation_iterations)) * weights.get(r.task_id, 1.0) for r in candidate_results)
        tokens_weighted = sum(r.tokens_used * weights.get(r.task_id, 1.0) for r in candidate_results)

        avg_latency = latency_weighted / total_weight
        avg_tokens = tokens_weighted / total_weight
        cost_efficiency = max(0.0, min(1.0, 1.0 - (avg_tokens / 6000.0)))

        return {
            "success_rate": round(success_weighted / total_weight, 4),
            "latency": round(avg_latency, 4),
            "cost": round(cost_efficiency, 4),
            "novelty": round(novelty_weighted / total_weight, 4),
            "retention": round(retention_weighted / total_weight, 4),
            "adaptation_speed": round(adapt_weighted / total_weight, 4),
            "quality": round(quality_weighted / total_weight, 4),
        }

    def run_ab(self, candidate_kpi: Dict[str, float]) -> Dict[str, Any]:
        comparisons = {}
        for baseline_name, baseline_kpi in self.baselines.items():
            comparisons[baseline_name] = {
                key: round(candidate_kpi.get(key, 0.0) - baseline_kpi.get(key, 0.0), 4)
                for key in ["success_rate", "cost", "novelty", "retention", "adaptation_speed"]
            }
            comparisons[baseline_name]["latency_delta"] = round(
                baseline_kpi.get("latency", 0.0) - candidate_kpi.get("latency", 0.0), 4
            )
        return comparisons

    def regression_gate(
        self,
        candidate_kpi: Dict[str, float],
        reference_kpi: Dict[str, float],
        tolerances: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        tol = tolerances or {
            "success_rate": 0.01,
            "cost": 0.02,
            "novelty": 0.02,
            "retention": 0.02,
            "adaptation_speed": 0.02,
            "quality": 0.02,
            "latency": 0.15,
        }

        violations = []
        for key in ["success_rate", "cost", "novelty", "retention", "adaptation_speed", "quality"]:
            if candidate_kpi.get(key, 0.0) + tol.get(key, 0.0) < reference_kpi.get(key, 0.0):
                violations.append({"metric": key, "candidate": candidate_kpi.get(key), "reference": reference_kpi.get(key)})

        candidate_latency = candidate_kpi.get("latency", 999.0)
        reference_latency = reference_kpi.get("latency", 999.0)
        if candidate_latency > reference_latency + tol.get("latency", 0.15):
            violations.append({"metric": "latency", "candidate": candidate_latency, "reference": reference_latency})

        return {
            "pass": len(violations) == 0,
            "violations": violations,
            "checked_at": datetime.now().isoformat(),
        }

    def save_reference(self, kpi: Dict[str, float], path: str = "core/evaluation/reference_kpi.json") -> str:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        payload = {"timestamp": datetime.now().isoformat(), "kpi": kpi}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return path

    def load_reference(self, path: str = "core/evaluation/reference_kpi.json") -> Dict[str, float]:
        if not os.path.exists(path):
            default = {
                "success_rate": 0.70,
                "latency": 4.2,
                "cost": 0.60,
                "novelty": 0.40,
                "retention": 0.55,
                "adaptation_speed": 0.45,
                "quality": 0.70,
            }
            return default
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("kpi", {})

    def build_report(self, candidate_name: str, kpi: Dict[str, float], gate: Dict[str, Any], ab: Dict[str, Any]) -> Dict[str, Any]:
        report = {
            "candidate": candidate_name,
            "kpi": kpi,
            "ab": ab,
            "gate": gate,
            "timestamp": datetime.now().isoformat(),
        }
        os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        return report


def build_eval_results_from_execution_history(history: List[Dict[str, Any]]) -> List[EvalResult]:
    results: List[EvalResult] = []
    if not history:
        return results

    for idx, item in enumerate(history[-6:]):
        score = float(item.get("score", 0.0))
        results.append(
            EvalResult(
                task_id=["s1", "s2", "m1", "m2", "h1", "h2"][idx % 6],
                success=bool(item.get("success", score >= 0.7)),
                latency_sec=float(item.get("time", 5.0)),
                tokens_used=max(200, int(2400 - (score * 800))),
                quality_score=score,
                novelty_score=max(0.1, min(1.0, 0.35 + score * 0.5)),
                retained=score >= 0.75,
                adaptation_iterations=max(1, 4 - int(score * 3)),
            )
        )
    return results
