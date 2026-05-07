import asyncio
from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class EvolutionStep:
    iteration: int
    code: str
    score: float
    improvement: str
    applied: bool


class EvolutionLoop:
    def __init__(self, max_iterations: int = 5):
        self.max_iterations = max_iterations
        self.history: list = []

    async def run(
        self,
        task: str,
        agent,
    ) -> Dict[str, Any]:
        current_code = None
        best_score = 0.0
        best_code = None
        
        for iteration in range(self.max_iterations):
            if iteration == 0:
                result = await agent.execute(task, learn=False)
                current_code = result.code
                current_score = result.test_score
            else:
                improved = await agent.improve(current_code)
                result = await agent.executor.execute(improved)
                
                if result["error"]:
                    continue
                
                test_result = await agent.test_runner.run_tests(improved)
                current_score = test_result["score"]
                current_code = improved
            
            if current_score > best_score:
                best_score = current_score
                best_code = current_code
                applied = True
            else:
                applied = False
            
            step = EvolutionStep(
                iteration=iteration,
                code=current_code,
                score=current_score,
                improvement=f"Iteration {iteration}: {current_score:.2%}",
                applied=applied,
            )
            self.history.append(step)
            
            if best_score >= 0.95:
                break
        
        return {
            "best_code": best_code,
            "best_score": best_score,
            "history": self.history,
            "total_iterations": len(self.history),
        }
