import asyncio
from datetime import datetime
from typing import Dict, Any

from core.agent import EvolvingAgent
from core.memory.hierarchical_v2 import HierarchicalMemorySystem, MemoryType
from core.critic.layer import CriticLayer
from core.structural_evolution.system import StructuralEvolution
from core.environment.interaction import EnvironmentInteraction
from core.strategy.long_term import LongTermStrategy


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
        
        self.execution_history = []
        self.improvement_mode = False

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
