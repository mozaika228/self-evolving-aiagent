from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum


class AgentRole(Enum):
    PLANNER = "planner"
    EXECUTOR = "executor"
    CRITIC = "critic"
    EVOLVER = "evolver"


@dataclass
class AgentTask:
    role: AgentRole
    task: str
    context: Dict[str, Any]
    priority: int = 1


class MultiAgentOrchestrator:
    def __init__(self):
        self.agents: Dict[AgentRole, Any] = {}
        self.task_queue: List[AgentTask] = []
        self.results: Dict[str, Any] = {}

    async def register_agent(self, role: AgentRole, agent: Any) -> None:
        self.agents[role] = agent

    async def plan(
        self,
        task: str,
        context: Dict[str, Any],
    ) -> str:
        planner = self.agents.get(AgentRole.PLANNER)
        if not planner:
            return task
        
        return await planner.plan(task, context)

    async def execute(
        self,
        plan: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        executor = self.agents.get(AgentRole.EXECUTOR)
        if not executor:
            return {}
        
        return await executor.execute(plan, context)

    async def critique(
        self,
        result: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        critic = self.agents.get(AgentRole.CRITIC)
        if not critic:
            return {"score": 0.5, "feedback": "No critic available"}
        
        return await critic.critique(result, context)

    async def evolve(
        self,
        feedback: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        evolver = self.agents.get(AgentRole.EVOLVER)
        if not evolver:
            return {}
        
        return await evolver.evolve(feedback, context)

    async def orchestrate(
        self,
        task: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        plan = await self.plan(task, context)
        result = await self.execute(plan, context)
        critique = await self.critique(result, context)
        evolution = await self.evolve(critique, context)
        
        return {
            "task": task,
            "plan": plan,
            "result": result,
            "critique": critique,
            "evolution": evolution,
        }
