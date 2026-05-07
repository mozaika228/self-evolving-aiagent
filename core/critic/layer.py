from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class CriticRole(Enum):
    QUALITY = "quality"              # Качество решения
    CORRECTNESS = "correctness"      # Корректность
    EFFICIENCY = "efficiency"        # Эффективность
    REUSABILITY = "reusability"      # Переиспользуемость


@dataclass
class CriticReview:
    success: bool
    score: float  # 0.0-1.0
    errors: List[str]
    improvements: List[str]
    should_save: bool
    reusable_as_skill: bool
    confidence: float
    timestamp: str
    reasoning: str


class CriticLayer:
    """Встроенный QA/Reviewer для самооценки агента"""
    
    def __init__(self):
        self.review_history: List[CriticReview] = []
        self.improvement_trends: Dict[str, float] = {}

    async def review(
        self,
        code: str,
        test_output: str,
        test_score: float,
        execution_time: float,
        task_description: str,
    ) -> CriticReview:
        """Провести критическую оценку решения"""
        
        # Оценка успеха
        success = test_score >= 0.7
        
        # Сбор ошибок
        errors = self._extract_errors(test_output)
        
        # Предложения по улучшению
        improvements = self._suggest_improvements(code, errors, test_score)
        
        # Оценка кода
        quality_score = await self._evaluate_quality(code, test_score)
        
        # Должны ли мы сохранить этот опыт?
        should_save = success and quality_score > 0.5
        
        # Может ли это стать скиллом?
        reusable = (
            success and
            quality_score > 0.7 and
            test_score > 0.9 and
            len(errors) == 0
        )
        
        # Уверенность в оценке
        confidence = self._calculate_confidence(test_score, len(errors))
        
        review = CriticReview(
            success=success,
            score=quality_score,
            errors=errors,
            improvements=improvements,
            should_save=should_save,
            reusable_as_skill=reusable,
            confidence=confidence,
            timestamp=datetime.now().isoformat(),
            reasoning=self._generate_reasoning(
                success, quality_score, reusable, errors
            ),
        )
        
        self.review_history.append(review)
        return review

    async def _evaluate_quality(self, code: str, test_score: float) -> float:
        """Оценить качество кода"""
        metrics = {
            "test_pass_rate": test_score,
            "has_docstring": 1.0 if '"""' in code or "'''" in code else 0.0,
            "has_error_handling": 1.0 if "try" in code and "except" in code else 0.3,
            "code_length_reasonable": 1.0 if 50 < len(code) < 10000 else 0.5,
            "has_type_hints": 1.0 if "->" in code else 0.5,
        }
        
        return sum(metrics.values()) / len(metrics)

    def _extract_errors(self, test_output: str) -> List[str]:
        """Извлечь ошибки из вывода тестов"""
        errors = []
        
        if "FAILED" in test_output:
            lines = test_output.split("\n")
            for line in lines:
                if "AssertionError" in line or "Error" in line:
                    errors.append(line.strip())
        
        return errors[:5]  # Топ 5 ошибок

    def _suggest_improvements(self, code: str, errors: List[str], score: float) -> List[str]:
        """Предложить улучшения"""
        improvements = []
        
        if score < 0.5:
            improvements.append("Fundamentally revise approach")
        elif score < 0.7:
            improvements.append("Fix critical logic errors")
        else:
            improvements.append("Optimize and refactor")
        
        if not any(doc in code for doc in ['"""', "'''", "#"]):
            improvements.append("Add documentation")
        
        if "try" not in code:
            improvements.append("Add error handling")
        
        if len(code) > 5000:
            improvements.append("Break into smaller functions")
        
        return improvements

    def _calculate_confidence(self, test_score: float, error_count: int) -> float:
        """Рассчитать уверенность в оценке"""
        score_confidence = min(test_score * 1.2, 1.0)  # 0-90% от теста
        error_penalty = min(error_count * 0.05, 0.3)  # -0% до -30% за ошибки
        return max(0.0, score_confidence - error_penalty)

    def _generate_reasoning(self, success: bool, score: float, reusable: bool, errors: List[str]) -> str:
        """Генерировать обоснование оценки"""
        if reusable:
            return "High-quality solution suitable for skill extraction"
        elif success:
            return f"Acceptable solution (score: {score:.1%}) but not production-ready"
        elif errors:
            return f"Solution has issues: {', '.join(errors[:2])}"
        else:
            return "Solution did not meet basic requirements"

    async def get_improvement_trajectory(self) -> Dict[str, Any]:
        """Анализ тренда улучшений"""
        if len(self.review_history) < 2:
            return {"trend": "insufficient_data"}
        
        scores = [r.score for r in self.review_history[-10:]]
        success_rate = sum(1 for r in self.review_history if r.success) / len(self.review_history)
        
        # Тренд
        if len(scores) >= 2:
            trend = "improving" if scores[-1] > scores[0] else "degrading"
        else:
            trend = "neutral"
        
        return {
            "trend": trend,
            "success_rate": success_rate,
            "avg_score": sum(scores) / len(scores),
            "recent_scores": scores,
            "reusable_solutions": sum(1 for r in self.review_history if r.reusable_as_skill),
        }
