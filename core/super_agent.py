import asyncio
from typing import Dict, Any
from datetime import datetime

from core.agent import EvolvingAgent
from core.skills.system import SkillSystem
from core.memory.hierarchical import HierarchicalMemory, MemoryLevel, MemoryEntry
from core.evaluation.system import EvaluationSystem
from core.evolution.loop import EvolutionLoop
from core.self_modification.runtime import SelfModificationRuntime
from core.multi_agent.orchestrator import MultiAgentOrchestrator, AgentRole
from core.genetics.evolver import GeneticEvolver


class SuperAgent:
    def __init__(
        self,
        model: str = "deepseek-coder:7b",
        max_iterations: int = 5,
    ):
        self.model = model
        self.max_iterations = max_iterations
        
        self.base_agent = EvolvingAgent(model=model, max_iterations=max_iterations)
        self.skill_system = SkillSystem()
        self.memory = HierarchicalMemory()
        self.evaluation = EvaluationSystem()
        self.evolution_loop = EvolutionLoop(max_iterations=max_iterations)
        self.self_mod = SelfModificationRuntime()
        self.multi_agent = MultiAgentOrchestrator()
        self.genetic_evolver = GeneticEvolver()

    async def execute_with_evolution(
        self,
        task: str,
        language: str = "python",
    ) -> Dict[str, Any]:
        start_time = datetime.now()
        
        result = await self.evolution_loop.run(task, self.base_agent)
        
        best_code = result["best_code"]
        best_score = result["best_score"]
        
        if best_score >= 0.8:
            skill = await self.skill_system.extract_skill(
                task=task,
                code=best_code,
                test_score=best_score,
            )
        
        eval_result = await self.evaluation.evaluate(
            task_id=task,
            code=best_code,
            test_score=best_score,
            latency=(datetime.now() - start_time).total_seconds(),
            quality_metrics={},
        )
        
        await self.memory.promote(
            content=best_code,
            from_level=MemoryLevel.L0_RAW,
            to_level=MemoryLevel.L1_INSIGHTS,
            score=best_score,
        )
        
        return {
            "task": task,
            "code": best_code,
            "score": best_score,
            "evaluation": eval_result,
            "skill_extracted": best_score >= 0.8,
            "time_elapsed": (datetime.now() - start_time).total_seconds(),
        }

    async def genetic_optimization(
        self,
        initial_code: str,
        generations: int = 10,
    ) -> Dict[str, Any]:
        await self.genetic_evolver.initialize(initial_code)
        
        async def fitness_fn(code: str) -> float:
            result = await self.base_agent.executor.execute(code)
            if result["error"]:
                return 0.0
            test_result = await self.base_agent.test_runner.run_tests(code)
            return test_result["score"]
        
        best_individual = None
        for gen in range(generations):
            await self.genetic_evolver.evaluate(fitness_fn)
            best_individual = await self.genetic_evolver.evolve()
        
        stats = await self.genetic_evolver.get_statistics()
        
        return {
            "best_code": best_individual.code,
            "best_fitness": best_individual.fitness,
            "generations": stats["generation"],
            "statistics": stats,
        }

    async def self_modify(
        self,
        code: str,
        tests: str,
        description: str,
    ) -> Dict[str, Any]:
        result = await self.self_mod.create_and_test(
            code=code,
            tests=tests,
            description=description,
        )
        
        if not result["success"]:
            result["code"] = await self.self_mod.rollback_if_failed(code, code)
        
        return result

    async def get_status(self) -> Dict[str, Any]:
        skill_stats = await self.skill_system.get_statistics()
        eval_stats = await self.evaluation.get_statistics()
        
        return {
            "skills": skill_stats,
            "evaluation": eval_stats,
            "memory_levels": {
                level.value: len(await self.memory.get_by_level(level))
                for level in MemoryLevel
            },
        }
