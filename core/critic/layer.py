from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List


class CriticRole(Enum):
    TESTS = "tests"
    STATIC_ANALYSIS = "static_analysis"
    RUNTIME_BEHAVIOR = "runtime_behavior"
    DOC_QUALITY = "doc_quality"
    COST_EFFICIENCY = "cost_efficiency"


@dataclass
class ImprovementItem:
    title: str
    priority: int
    source: str
    rationale: str
    created_at: str
    status: str = "open"


@dataclass
class CriticReview:
    success: bool
    score: float
    errors: List[str]
    improvements: List[str]
    should_save: bool
    reusable_as_skill: bool
    confidence: float
    timestamp: str
    reasoning: str
    judges: Dict[str, float] = field(default_factory=dict)
    counterfactual: Dict[str, Any] = field(default_factory=dict)
    backlog: List[Dict[str, Any]] = field(default_factory=list)


class CriticLayer:
    """Critic Layer v2: multi-judge review + counterfactual + improvement backlog."""

    def __init__(self):
        self.review_history: List[CriticReview] = []
        self.improvement_backlog: List[ImprovementItem] = []

    async def review(
        self,
        code: str,
        test_output: str,
        test_score: float,
        execution_time: float,
        task_description: str,
    ) -> CriticReview:
        errors = self._extract_errors(test_output)

        judges = {
            CriticRole.TESTS.value: self._judge_tests(test_score, errors),
            CriticRole.STATIC_ANALYSIS.value: self._judge_static_analysis(code),
            CriticRole.RUNTIME_BEHAVIOR.value: self._judge_runtime_behavior(code, test_output),
            CriticRole.DOC_QUALITY.value: self._judge_doc_quality(code),
            CriticRole.COST_EFFICIENCY.value: self._judge_cost_efficiency(code, execution_time),
        }

        weights = {
            CriticRole.TESTS.value: 0.35,
            CriticRole.STATIC_ANALYSIS.value: 0.2,
            CriticRole.RUNTIME_BEHAVIOR.value: 0.2,
            CriticRole.DOC_QUALITY.value: 0.1,
            CriticRole.COST_EFFICIENCY.value: 0.15,
        }
        score = sum(judges[key] * weights[key] for key in judges)

        success = score >= 0.68 and judges[CriticRole.TESTS.value] >= 0.6
        reusable = success and score > 0.82 and len(errors) == 0 and judges[CriticRole.DOC_QUALITY.value] > 0.6
        should_save = success and score >= 0.6

        improvements = self._suggest_improvements(code, errors, judges)
        counterfactual = self._counterfactual_assessment(score, judges, execution_time)
        backlog = self._build_backlog(improvements, judges, counterfactual)

        confidence = self._calculate_confidence(judges, len(errors))
        reasoning = self._generate_reasoning(success, score, judges, counterfactual)

        review = CriticReview(
            success=success,
            score=score,
            errors=errors,
            improvements=improvements,
            should_save=should_save,
            reusable_as_skill=reusable,
            confidence=confidence,
            timestamp=datetime.now().isoformat(),
            reasoning=reasoning,
            judges=judges,
            counterfactual=counterfactual,
            backlog=[item.__dict__ for item in backlog],
        )
        self.review_history.append(review)
        return review

    def _judge_tests(self, test_score: float, errors: List[str]) -> float:
        penalty = min(0.25, len(errors) * 0.05)
        return max(0.0, min(1.0, test_score - penalty))

    def _judge_static_analysis(self, code: str) -> float:
        score = 1.0
        if "TODO" in code or "FIXME" in code:
            score -= 0.2
        if len(code) > 12000:
            score -= 0.2
        if code.count("def ") <= 1 and len(code) > 600:
            score -= 0.2
        if "eval(" in code:
            score -= 0.3
        return max(0.0, min(1.0, score))

    def _judge_runtime_behavior(self, code: str, test_output: str) -> float:
        score = 0.7
        if "timeout" in test_output.lower():
            score -= 0.4
        if "error" in test_output.lower() or "traceback" in test_output.lower():
            score -= 0.25
        if "try" in code and "except" in code:
            score += 0.15
        return max(0.0, min(1.0, score))

    def _judge_doc_quality(self, code: str) -> float:
        has_docstring = '"""' in code or "'''" in code
        has_comments = "#" in code
        has_type_hints = "->" in code
        score = 0.2
        if has_docstring:
            score += 0.4
        if has_comments:
            score += 0.2
        if has_type_hints:
            score += 0.2
        return max(0.0, min(1.0, score))

    def _judge_cost_efficiency(self, code: str, execution_time: float) -> float:
        score = 1.0
        if execution_time > 20:
            score -= 0.5
        elif execution_time > 10:
            score -= 0.25
        if len(code) > 5000:
            score -= 0.15
        return max(0.0, min(1.0, score))

    def _extract_errors(self, test_output: str) -> List[str]:
        errors = []
        lines = test_output.split("\n")
        for line in lines:
            normalized = line.strip()
            if any(token in normalized for token in ["FAILED", "AssertionError", "Traceback", "Error"]):
                errors.append(normalized)
        return errors[:8]

    def _suggest_improvements(self, code: str, errors: List[str], judges: Dict[str, float]) -> List[str]:
        suggestions: List[str] = []
        if judges[CriticRole.TESTS.value] < 0.7:
            suggestions.append("Increase test reliability and fix failing logic paths")
        if judges[CriticRole.STATIC_ANALYSIS.value] < 0.75:
            suggestions.append("Refactor structure and remove risky constructs")
        if judges[CriticRole.RUNTIME_BEHAVIOR.value] < 0.7:
            suggestions.append("Improve runtime safety and exception handling")
        if judges[CriticRole.DOC_QUALITY.value] < 0.65:
            suggestions.append("Add docstrings, comments and type hints")
        if judges[CriticRole.COST_EFFICIENCY.value] < 0.7:
            suggestions.append("Optimize for latency and code footprint")
        if errors and "Add error handling" not in suggestions:
            suggestions.append("Add targeted error guards for observed failures")
        return suggestions

    def _counterfactual_assessment(
        self,
        score: float,
        judges: Dict[str, float],
        execution_time: float,
    ) -> Dict[str, Any]:
        alt_with_better_docs = min(1.0, score + (1.0 - judges[CriticRole.DOC_QUALITY.value]) * 0.08)
        alt_with_faster_runtime = min(
            1.0,
            score + (0.08 if execution_time > 8 else 0.03),
        )
        alt_with_stronger_tests = min(
            1.0,
            score + (1.0 - judges[CriticRole.TESTS.value]) * 0.2,
        )

        best_alt = max(alt_with_better_docs, alt_with_faster_runtime, alt_with_stronger_tests)
        regret = max(0.0, best_alt - score)
        return {
            "alternatives": {
                "better_docs": round(alt_with_better_docs, 4),
                "faster_runtime": round(alt_with_faster_runtime, 4),
                "stronger_tests": round(alt_with_stronger_tests, 4),
            },
            "best_possible_score": round(best_alt, 4),
            "regret": round(regret, 4),
            "recommendation": "shift_strategy" if regret > 0.1 else "incremental_improve",
        }

    def _build_backlog(
        self,
        improvements: List[str],
        judges: Dict[str, float],
        counterfactual: Dict[str, Any],
    ) -> List[ImprovementItem]:
        created: List[ImprovementItem] = []

        priority_base = 90 if counterfactual.get("regret", 0) > 0.1 else 70
        for idx, improvement in enumerate(improvements):
            item = ImprovementItem(
                title=improvement,
                priority=max(1, priority_base - idx * 10),
                source="critic_v2",
                rationale=f"judge_snapshot={judges}",
                created_at=datetime.now().isoformat(),
            )
            self.improvement_backlog.append(item)
            created.append(item)

        self.improvement_backlog.sort(key=lambda x: x.priority, reverse=True)
        self.improvement_backlog = self.improvement_backlog[:100]
        return created

    def _calculate_confidence(self, judges: Dict[str, float], error_count: int) -> float:
        dispersion = max(judges.values()) - min(judges.values())
        base = sum(judges.values()) / len(judges)
        penalty = min(0.35, error_count * 0.04 + dispersion * 0.2)
        return max(0.0, min(1.0, base - penalty))

    def _generate_reasoning(
        self,
        success: bool,
        score: float,
        judges: Dict[str, float],
        counterfactual: Dict[str, Any],
    ) -> str:
        weakest = min(judges, key=judges.get)
        if success:
            return (
                f"Solution accepted with score {score:.1%}; "
                f"weakest axis: {weakest}; "
                f"counterfactual regret: {counterfactual.get('regret', 0):.2f}"
            )
        return (
            f"Solution rejected with score {score:.1%}; "
            f"weakest axis: {weakest}; "
            f"recommended mode: {counterfactual.get('recommendation', 'incremental_improve')}"
        )

    async def get_improvement_trajectory(self) -> Dict[str, Any]:
        if len(self.review_history) < 2:
            return {
                "trend": "insufficient_data",
                "backlog_size": len(self.improvement_backlog),
            }

        scores = [r.score for r in self.review_history[-10:]]
        trend = "improving" if scores[-1] > scores[0] else "degrading"
        success_rate = sum(1 for r in self.review_history if r.success) / len(self.review_history)

        return {
            "trend": trend,
            "success_rate": success_rate,
            "avg_score": sum(scores) / len(scores),
            "recent_scores": scores,
            "reusable_solutions": sum(1 for r in self.review_history if r.reusable_as_skill),
            "backlog_size": len(self.improvement_backlog),
            "top_backlog": [item.__dict__ for item in self.improvement_backlog[:5]],
        }

    async def get_improvement_backlog(self, limit: int = 20) -> List[Dict[str, Any]]:
        return [item.__dict__ for item in self.improvement_backlog[:limit]]
