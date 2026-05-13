import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List

from core.agent import EvolvingAgent
from core.memory.hierarchical_v2 import HierarchicalMemorySystem, MemoryType
from core.critic.layer import CriticLayer
from core.structural_evolution.system import StructuralEvolution
from core.environment.interaction import EnvironmentInteraction
from core.strategy.long_term import LongTermStrategy
from core.evaluation.lab import EvaluationLab, build_eval_results_from_execution_history


class FullyEvolvedAgent:
    """Полностью эволюционирующий агент с самооценкой и стратегией"""
    
    def __init__(self, model: str = "deepseek-coder:7b"):
        self.base_agent = EvolvingAgent(model=model)
        
        # Новые компоненты
        self.memory = HierarchicalMemorySystem()
        self.critic = CriticLayer()
        self.structural_evolution = StructuralEvolution()
        self.environment = EnvironmentInteraction()
        self.strategy = LongTermStrategy()
        self.evaluation_lab = EvaluationLab()
        
        self.execution_history = []
        self.improvement_mode = False
        self.last_weekly_skill_snapshot: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "tools": [],
            "skill_memory_count": 0,
        }

    async def execute_with_full_evolution(
        self,
        task: str,
        language: str = "python",
    ) -> Dict[str, Any]:
        """Выполнение с полной эволюцией"""
        start_time = datetime.now()
        
        # 1. Поиск в памяти похожие решения
        similar = await self.memory.retrieve(
            query=task,
            memory_type=MemoryType.SKILL,
            top_k=3,
        )
        
        context = f"Similar successful patterns found: {len(similar)}\n"
        if similar:
            context += "\n".join([str(s.content)[:200] for s in similar])
        
        # 2. Выполнение
        result = await self.base_agent.execute(
            task=task,
            language=language,
            learn=False,
        )
        
        # 3. Критическая оценка
        review = await self.critic.review(
            code=result.code,
            test_output=result.tests_output,
            test_score=result.test_score,
            execution_time=0.0,
            task_description=task,
        )
        
        # 4. Сохранение в иерархию памяти
        if review.should_save:
            memory_type = MemoryType.SKILL if review.reusable_as_skill else MemoryType.LONG_TERM
            await self.memory.store(
                content=result.code,
                memory_type=memory_type,
                importance=review.score,
            )
        
        # 5. Автоматическое улучшение на основе критики
        improvement_result = await self.strategy.auto_initiate_improvement({
            "success": review.success,
            "confidence": review.confidence,
            "improvements": review.improvements,
            "counterfactual": review.counterfactual,
        })
        
        # 6. Обнаружение повторяющихся паттернов
        patterns = await self.structural_evolution.detect_repeating_patterns(
            self.execution_history[-10:]
        )
        
        # 7. Создание инструментов из паттернов
        new_tools = 0
        for pattern in patterns[:1]:  # Используем топ паттерн
            tool_result = await self.structural_evolution.create_custom_tool(
                pattern_steps=pattern["pattern"],
                pattern_name=f"tool_{len(self.structural_evolution.custom_tools)}",
            )
            new_tools += 1
        
        # 8. Консолидация памяти
        await self.memory.consolidate_memory()
        await self.memory.natural_forgetting()
        
        # 9. Собрать статус
        memory_stats = await self.memory.get_memory_stats()
        improvement_trajectory = await self.critic.get_improvement_trajectory()
        evolution_report = await self.structural_evolution.get_evolution_report()
        strategy_status = await self.strategy.get_strategic_status()
        
        execution_time = (datetime.now() - start_time).total_seconds()

        estimated_tokens = max(200, len(result.code) // 3)
        await self.strategy.update_kpi(
            success=review.success,
            quality_score=review.score,
            latency_sec=execution_time,
            tokens_spent=estimated_tokens,
        )
        await self.strategy.build_iteration_plan(n_iterations=5)
        
        # Записать в историю
        self.execution_history.append({
            "task": task,
            "score": result.test_score,
            "success": review.success,
            "time": execution_time,
            "steps": ["retrieve", "execute", "review", "store", "improve"],
        })
        
        return {
            "task": task,
            "code": result.code,
            "execution": {
                "score": result.test_score,
                "time": execution_time,
                "iterations": result.iterations,
            },
            "criticism": {
                "success": review.success,
                "quality_score": review.score,
                "errors": review.errors,
                "improvements": review.improvements,
                "reusable_as_skill": review.reusable_as_skill,
                "confidence": review.confidence,
                "reasoning": review.reasoning,
                "judges": review.judges,
                "counterfactual": review.counterfactual,
                "backlog": review.backlog,
            },
            "memory": memory_stats,
            "evolution": {
                "patterns_detected": len(patterns),
                "new_tools_created": new_tools,
                "structural_changes": evolution_report["total_efficiency_gain"],
                "registry": evolution_report.get("registry", {}),
            },
            "improvement": improvement_result,
            "trajectory": improvement_trajectory,
            "strategy": strategy_status,
        }

    async def get_full_status(self) -> Dict[str, Any]:
        """Полный статус агента"""
        return {
            "memory": await self.memory.get_memory_stats(),
            "critic": await self.critic.get_improvement_trajectory(),
            "evolution": await self.structural_evolution.get_evolution_report(),
            "environment": await self.environment.get_environment_stats(),
            "strategy": await self.strategy.get_strategic_status(),
            "execution_history_size": len(self.execution_history),
        }

    async def run_nightly_memory_maintenance(self) -> Dict[str, Any]:
        return await self.memory.nightly_maintenance()

    async def run_evaluation_lab(self, candidate_name: str = "current_agent") -> Dict[str, Any]:
        eval_results = build_eval_results_from_execution_history(self.execution_history)
        candidate_kpi = self.evaluation_lab.evaluate_candidate(eval_results)
        reference_kpi = self.evaluation_lab.load_reference()
        gate = self.evaluation_lab.regression_gate(candidate_kpi, reference_kpi)
        ab = self.evaluation_lab.run_ab(candidate_kpi)
        report = self.evaluation_lab.build_report(candidate_name, candidate_kpi, gate, ab)
        return report

    async def save_evaluation_reference(self, candidate_name: str = "current_agent") -> Dict[str, Any]:
        report = await self.run_evaluation_lab(candidate_name=candidate_name)
        path = self.evaluation_lab.save_reference(report["kpi"])
        return {"saved": True, "path": path, "kpi": report["kpi"]}

    async def run_evolution_cycle(self, task: str, language: str = "python") -> Dict[str, Any]:
        result = await self.execute_with_full_evolution(task=task, language=language)
        control_plane = await self.get_control_plane_status()
        return {"cycle": result, "control_plane": control_plane}

    async def get_control_plane_status(self) -> Dict[str, Any]:
        memory = await self.memory.get_memory_stats()
        evolution = await self.structural_evolution.get_evolution_report()
        strategy = await self.strategy.get_strategic_status()
        critic = await self.critic.get_improvement_trajectory()
        environment = await self.environment.get_environment_stats()

        risks: List[Dict[str, Any]] = []
        if strategy.get("safe_mode"):
            risks.append({"level": "high", "type": "safe_mode", "reason": strategy.get("safe_mode_reason", "")})
        if critic.get("trend") == "degrading":
            risks.append({"level": "medium", "type": "quality_trend", "reason": "critic trend is degrading"})
        disabled_tools = evolution.get("registry", {}).get("disabled", 0)
        if disabled_tools > 0:
            risks.append({"level": "medium", "type": "tool_degradation", "reason": f"{disabled_tools} tools disabled"})
        if memory.get("total_entries", 0) == 0:
            risks.append({"level": "low", "type": "cold_memory", "reason": "memory has no retained entries"})

        return {
            "timestamp": datetime.now().isoformat(),
            "memory": memory,
            "evolution": evolution,
            "strategy": strategy,
            "critic": critic,
            "environment": environment,
            "risks": risks,
        }

    async def generate_weekly_evolution_report(self) -> Dict[str, Any]:
        cutoff = datetime.now() - timedelta(days=7)
        recent = []
        for item in self.execution_history:
            # history currently has no explicit timestamp; infer by recency order
            recent.append(item)
        recent = recent[-50:]

        total = len(recent)
        success = sum(1 for x in recent if x.get("success"))
        avg_score = (sum(x.get("score", 0.0) for x in recent) / total) if total else 0.0
        avg_time = (sum(x.get("time", 0.0) for x in recent) / total) if total else 0.0

        registry = await self.structural_evolution.get_registry_report()
        memory_stats = await self.memory.get_memory_stats()

        current_snapshot = {
            "timestamp": datetime.now().isoformat(),
            "tools": [item["name"] for item in registry.get("top_rated", [])],
            "skill_memory_count": memory_stats.get("layers", {}).get("skill", {}).get("count", 0),
        }
        previous = self.last_weekly_skill_snapshot
        prev_tools = set(previous.get("tools", []))
        cur_tools = set(current_snapshot["tools"])
        diff = {
            "added_tools": sorted(list(cur_tools - prev_tools)),
            "removed_tools": sorted(list(prev_tools - cur_tools)),
            "skill_memory_delta": current_snapshot["skill_memory_count"] - previous.get("skill_memory_count", 0),
        }
        self.last_weekly_skill_snapshot = current_snapshot

        return {
            "period_days": 7,
            "summary": {
                "executions": total,
                "success_rate": (success / total) if total else 0.0,
                "avg_score": avg_score,
                "avg_time_sec": avg_time,
            },
            "skill_diff": diff,
            "registry": registry,
            "generated_at": datetime.now().isoformat(),
        }
