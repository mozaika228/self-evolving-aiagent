import asyncio
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime

from core.llm_engine import LLMEngine
from core.executor import CodeExecutor
from core.code_gen.generator import CodeGenerator
from core.testing.test_runner import TestRunner
from core.memory.vector_store import VectorStore
from core.rl.reward_model import RewardModel
from core.rl.trainer import RLTrainer


@dataclass
class ExecutionResult:
    code: str
    test_score: float
    quality_metrics: Dict[str, float]
    tests_output: str
    improvement: str
    iterations: int
    total_time: float
    errors: list


class EvolvingAgent:
    def __init__(
        self,
        model: str = "deepseek-coder:7b",
        max_iterations: int = 5,
        ollama_host: str = "http://localhost:11434",
    ):
        self.model = model
        self.max_iterations = max_iterations
        
        self.llm = LLMEngine(model=model, host=ollama_host)
        self.executor = CodeExecutor()
        self.generator = CodeGenerator(llm=self.llm)
        self.test_runner = TestRunner()
        self.vector_store = VectorStore()
        self.reward_model = RewardModel()
        self.rl_trainer = RLTrainer()

    async def execute(
        self,
        task: str,
        language: str = "python",
        learn: bool = True,
    ) -> ExecutionResult:
        start_time = asyncio.get_event_loop().time()
        iterations = 0
        best_code = None
        best_score = 0.0
        errors = []
        improvements = []

        for iteration in range(self.max_iterations):
            iterations += 1

            if iteration == 0:
                similar = await self.vector_store.search(task, limit=3)
                context = self._format_context(similar)
                code = await self.generator.generate(
                    task=task,
                    language=language,
                    context=context,
                )
            else:
                error_context = errors[-1] if errors else ""
                improvement_prompt = f"Fix the following error:\n{error_context}"
                code = await self.generator.generate(
                    task=improvement_prompt,
                    language=language,
                )

            result = await self.executor.execute(code, language=language)
            
            if result["error"]:
                errors.append(result["error"])
                continue

            test_result = await self.test_runner.run_tests(
                code=code,
                language=language,
            )
            
            metrics = test_result["metrics"]
            test_score = test_result["score"]

            if test_score > best_score:
                best_score = test_score
                best_code = code
                improvements.append(
                    f"Iteration {iteration}: score {best_score:.2%}"
                )

            if test_score >= 0.95:
                break

        total_time = asyncio.get_event_loop().time() - start_time

        if learn and best_code:
            await self._learn_from_success(
                task=task,
                code=best_code,
                score=best_score,
                iterations=iterations,
            )

        return ExecutionResult(
            code=best_code or "",
            test_score=best_score,
            quality_metrics=metrics if best_code else {},
            tests_output=test_result.get("output", "") if best_code else "",
            improvement="\n".join(improvements),
            iterations=iterations,
            total_time=total_time,
            errors=errors,
        )

    async def improve(self, code: str, language: str = "python") -> str:
        metrics = await self.test_runner.get_quality_metrics(code, language)
        
        issues = []
        if metrics.get("coverage", 0) < 0.8:
            issues.append("Low test coverage")
        if metrics.get("complexity", 0) > 10:
            issues.append("High cyclomatic complexity")
        if not metrics.get("has_docstring", False):
            issues.append("Missing docstrings")

        if not issues:
            return code

        improvement_prompt = f"Improve this code. Issues: {', '.join(issues)}\n\n{code}"
        improved = await self.generator.generate(
            task=improvement_prompt,
            language=language,
        )
        return improved

    async def reflect_and_improve(self) -> Dict[str, Any]:
        stats = await self.vector_store.get_statistics()
        
        if stats["total_solutions"] < 5:
            return {"status": "insufficient_data", "message": "Not enough solutions to analyze"}

        high_performers = await self.vector_store.search_by_score(min_score=0.9)
        
        patterns = self._extract_patterns(high_performers)
        
        policy_update = await self.rl_trainer.update_policy(
            patterns=patterns,
            stats=stats,
        )

        return {
            "status": "success",
            "patterns_found": len(patterns),
            "policy_version": policy_update.get("version"),
            "avg_reward": policy_update.get("avg_reward"),
        }

    async def _learn_from_success(
        self,
        task: str,
        code: str,
        score: float,
        iterations: int,
    ) -> None:
        reward = self.reward_model.calculate(
            test_score=score,
            iterations=iterations,
            code_quality=score,
        )

        await self.vector_store.add_solution(
            task=task,
            code=code,
            score=score,
            reward=reward,
            timestamp=datetime.now().isoformat(),
        )

        await self.rl_trainer.add_experience(
            task=task,
            code=code,
            reward=reward,
            score=score,
        )

    def _format_context(self, similar_solutions: list) -> str:
        if not similar_solutions:
            return ""

        context = "Similar solutions:\n"
        for solution in similar_solutions:
            context += f"\n# Score: {solution['score']:.2%}\n{solution['code'][:500]}...\n"
        return context

    def _extract_patterns(self, high_performers: list) -> list:
        patterns = []
        for solution in high_performers:
            patterns.append({
                "code": solution["code"],
                "score": solution["score"],
                "features": self._analyze_code_features(solution["code"]),
            })
        return patterns

    def _analyze_code_features(self, code: str) -> Dict[str, Any]:
        return {
            "length": len(code),
            "has_tests": "def test_" in code or "@pytest" in code,
            "has_docstring": '"""' in code or "'''" in code,
            "has_error_handling": "try" in code and "except" in code,
            "functions_count": code.count("def "),
        }
