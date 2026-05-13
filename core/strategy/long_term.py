from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional


class GoalPriority(Enum):
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    OPTIONAL = 1


class GoalStatus(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    ABANDONED = "abandoned"


@dataclass
class Goal:
    description: str
    priority: GoalPriority
    deadline: Optional[str] = None
    subtasks: List[str] = field(default_factory=list)
    status: GoalStatus = GoalStatus.ACTIVE
    progress: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def is_overdue(self) -> bool:
        return bool(self.deadline and datetime.now() > datetime.fromisoformat(self.deadline))


@dataclass
class Budget:
    token_budget_total: int = 120000
    token_budget_remaining: int = 120000
    time_budget_sec_total: float = 1800.0
    time_budget_sec_remaining: float = 1800.0


class LongTermStrategy:
    """Meta-controller v2: goals + KPI + budget + N-iteration planning + safe mode."""

    def __init__(self):
        self.goals: Dict[str, Goal] = {}
        self.skill_improvement_queue: List[str] = []
        self.weakness_detection: Dict[str, float] = {}
        self.strategy_iterations = 0

        self.kpi: Dict[str, float] = {
            "success_rate": 0.0,
            "quality_score": 0.0,
            "latency_sec": 0.0,
            "cost_efficiency": 0.0,
        }
        self.kpi_history: List[Dict[str, Any]] = []
        self.budget = Budget()
        self.safe_mode = False
        self.safe_mode_reason = ""

        self.self_improvement_backlog: List[Dict[str, Any]] = []
        self.iteration_plan: List[Dict[str, Any]] = []

    async def set_goal(
        self,
        goal_id: str,
        description: str,
        priority: GoalPriority,
        deadline_hours: Optional[int] = None,
    ) -> Dict[str, Any]:
        deadline = (datetime.now() + timedelta(hours=deadline_hours)).isoformat() if deadline_hours else None
        self.goals[goal_id] = Goal(description=description, priority=priority, deadline=deadline)
        return {"goal_id": goal_id, "status": "created", "priority": priority.name}

    async def update_kpi(
        self,
        success: bool,
        quality_score: float,
        latency_sec: float,
        tokens_spent: int,
    ) -> Dict[str, Any]:
        self.strategy_iterations += 1
        self.budget.token_budget_remaining = max(0, self.budget.token_budget_remaining - max(0, tokens_spent))
        self.budget.time_budget_sec_remaining = max(0.0, self.budget.time_budget_sec_remaining - max(0.0, latency_sec))

        prev = self.kpi.copy()
        alpha = 0.25
        self.kpi["success_rate"] = (1 - alpha) * self.kpi["success_rate"] + alpha * (1.0 if success else 0.0)
        self.kpi["quality_score"] = (1 - alpha) * self.kpi["quality_score"] + alpha * quality_score
        self.kpi["latency_sec"] = (1 - alpha) * self.kpi["latency_sec"] + alpha * latency_sec

        budget_ratio = 0.0
        if self.budget.token_budget_total > 0 and self.budget.time_budget_sec_total > 0:
            token_ratio = self.budget.token_budget_remaining / self.budget.token_budget_total
            time_ratio = self.budget.time_budget_sec_remaining / self.budget.time_budget_sec_total
            budget_ratio = (token_ratio + time_ratio) / 2.0
        self.kpi["cost_efficiency"] = max(0.0, min(1.0, budget_ratio))

        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "iteration": self.strategy_iterations,
            "kpi": self.kpi.copy(),
            "delta": {k: self.kpi[k] - prev[k] for k in self.kpi},
        }
        self.kpi_history.append(snapshot)
        self.kpi_history = self.kpi_history[-200:]

        await self._evaluate_safe_mode()
        return {"kpi": self.kpi.copy(), "safe_mode": self.safe_mode}

    async def build_iteration_plan(self, n_iterations: int = 5) -> List[Dict[str, Any]]:
        plan: List[Dict[str, Any]] = []
        base_focus = "stability" if self.safe_mode else "capability_growth"
        top_tasks = self.prioritize_self_improvement(limit=max(1, n_iterations))

        for i in range(1, n_iterations + 1):
            task = top_tasks[i - 1] if i - 1 < len(top_tasks) else {
                "task": f"maintain_{base_focus}_{i}",
                "priority": 40,
                "reason": "fill_plan",
            }
            plan.append(
                {
                    "iteration": i,
                    "focus": base_focus,
                    "task": task["task"],
                    "priority": task["priority"],
                    "guardrails": "strict" if self.safe_mode else "normal",
                    "budget_hint": {
                        "tokens": int(self.budget.token_budget_remaining / max(1, n_iterations)),
                        "time_sec": round(self.budget.time_budget_sec_remaining / max(1, n_iterations), 2),
                    },
                }
            )

        self.iteration_plan = plan
        return plan

    async def detect_weaknesses(self, recent_failures: List[Dict], skill_stats: Dict[str, Any]) -> Dict[str, Any]:
        weaknesses: Dict[str, float] = {}
        failure_patterns: Dict[str, int] = {}

        for failure in recent_failures:
            task_type = failure.get("task_type", "unknown")
            failure_patterns[task_type] = failure_patterns.get(task_type, 0) + 1

        for task_type, count in failure_patterns.items():
            if count >= 2:
                severity = min(1.0, 0.25 * count)
                weaknesses[f"task_{task_type}"] = severity

        self.weakness_detection.update(weaknesses)
        for name, severity in weaknesses.items():
            if severity >= 0.4:
                self._enqueue_improvement(name, severity, "failure_pattern")

        return {
            "weaknesses_detected": len(weaknesses),
            "improvement_queue": self.prioritize_self_improvement(limit=5),
            "suggested_focus": list(weaknesses.keys())[:3],
        }

    async def auto_initiate_improvement(self, critic_feedback: Dict[str, Any]) -> Dict[str, Any]:
        triggered = False
        improvements = critic_feedback.get("improvements", [])
        confidence = critic_feedback.get("confidence", 0.0)
        counterfactual = critic_feedback.get("counterfactual", {})
        regret = float(counterfactual.get("regret", 0.0))

        if not critic_feedback.get("success") and confidence >= 0.65:
            for item in improvements:
                self._enqueue_improvement(item, min(1.0, 0.55 + regret), "critic_failure")
                triggered = True

        if regret >= 0.1:
            self._enqueue_improvement("counterfactual_strategy_shift", min(1.0, 0.6 + regret), "counterfactual")
            triggered = True

        prioritized = self.prioritize_self_improvement(limit=8)
        return {
            "auto_improvement": triggered,
            "improvement_queue_size": len(self.self_improvement_backlog),
            "top_improvements": prioritized[:3],
            "safe_mode": self.safe_mode,
        }

    def prioritize_self_improvement(self, limit: int = 10) -> List[Dict[str, Any]]:
        ranked = sorted(self.self_improvement_backlog, key=lambda x: x["priority"], reverse=True)
        return ranked[:limit]

    async def set_budget(self, token_budget: int, time_budget_sec: float) -> Dict[str, Any]:
        self.budget.token_budget_total = max(1, token_budget)
        self.budget.token_budget_remaining = min(self.budget.token_budget_remaining, self.budget.token_budget_total)
        self.budget.time_budget_sec_total = max(1.0, time_budget_sec)
        self.budget.time_budget_sec_remaining = min(
            self.budget.time_budget_sec_remaining,
            self.budget.time_budget_sec_total,
        )
        return {
            "token_budget_total": self.budget.token_budget_total,
            "time_budget_sec_total": self.budget.time_budget_sec_total,
        }

    async def _evaluate_safe_mode(self) -> None:
        reason = ""
        if self.kpi["quality_score"] < 0.45 and self.strategy_iterations >= 3:
            reason = "quality_drop"
        elif self.kpi["success_rate"] < 0.4 and self.strategy_iterations >= 4:
            reason = "low_success_rate"
        elif self.budget.token_budget_remaining <= int(0.1 * self.budget.token_budget_total):
            reason = "token_budget_low"
        elif self.budget.time_budget_sec_remaining <= 0.1 * self.budget.time_budget_sec_total:
            reason = "time_budget_low"

        self.safe_mode = bool(reason)
        self.safe_mode_reason = reason

    def _enqueue_improvement(self, task: str, severity: float, reason: str) -> None:
        priority = int(min(100, max(1, severity * 100)))
        existing = next((x for x in self.self_improvement_backlog if x["task"] == task), None)
        if existing:
            existing["priority"] = max(existing["priority"], priority)
            existing["reason"] = reason
            existing["updated_at"] = datetime.now().isoformat()
            return

        self.self_improvement_backlog.append(
            {
                "task": task,
                "priority": priority,
                "reason": reason,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
        )
        self.self_improvement_backlog = sorted(
            self.self_improvement_backlog,
            key=lambda x: x["priority"],
            reverse=True,
        )[:200]

    async def get_strategic_status(self) -> Dict[str, Any]:
        active_goals = [g for g in self.goals.values() if g.status == GoalStatus.ACTIVE]
        completed_goals = [g for g in self.goals.values() if g.status == GoalStatus.COMPLETED]

        return {
            "active_goals": len(active_goals),
            "completed_goals": len(completed_goals),
            "weaknesses": len(self.weakness_detection),
            "improvement_queue_size": len(self.self_improvement_backlog),
            "strategy_iterations": self.strategy_iterations,
            "next_improvement_targets": self.prioritize_self_improvement(limit=3),
            "kpi": self.kpi,
            "budget": {
                "token_budget_total": self.budget.token_budget_total,
                "token_budget_remaining": self.budget.token_budget_remaining,
                "time_budget_sec_total": self.budget.time_budget_sec_total,
                "time_budget_sec_remaining": round(self.budget.time_budget_sec_remaining, 3),
            },
            "safe_mode": self.safe_mode,
            "safe_mode_reason": self.safe_mode_reason,
            "iteration_plan_preview": self.iteration_plan[:3],
        }
