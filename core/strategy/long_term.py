from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta


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
    deadline: str = None
    subtasks: List[str] = None
    status: GoalStatus = GoalStatus.ACTIVE
    progress: float = 0.0
    created_at: str = ""
    
    def is_overdue(self) -> bool:
        if not self.deadline:
            return False
        return datetime.now() > datetime.fromisoformat(self.deadline)


class LongTermStrategy:
    """Долгосрочное планирование и стратегия агента"""
    
    def __init__(self):
        self.goals: Dict[str, Goal] = {}
        self.skill_improvement_queue: List[str] = []  # Навыки для улучшения
        self.weakness_detection: Dict[str, float] = {}  # Обнаруженные слабости
        self.strategy_iterations = 0

    async def set_goal(
        self,
        goal_id: str,
        description: str,
        priority: GoalPriority,
        deadline_hours: int = None,
    ) -> Dict[str, Any]:
        """Установить долгосрочную цель"""
        
        deadline = None
        if deadline_hours:
            deadline = (datetime.now() + timedelta(hours=deadline_hours)).isoformat()
        
        goal = Goal(
            description=description,
            priority=priority,
            deadline=deadline,
            subtasks=[],
            created_at=datetime.now().isoformat(),
        )
        
        self.goals[goal_id] = goal
        
        return {
            "goal_id": goal_id,
            "status": "created",
            "priority": priority.name,
        }

    async def detect_weaknesses(
        self,
        recent_failures: List[Dict],
        skill_stats: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Обнаружить слабые места и предложить улучшения"""
        
        weaknesses = {}
        
        # Анализируем неудачи
        failure_patterns = {}
        for failure in recent_failures:
            task_type = failure.get("task_type", "unknown")
            failure_patterns[task_type] = failure_patterns.get(task_type, 0) + 1
        
        # Определяем часто ошибочные типы задач
        for task_type, count in failure_patterns.items():
            if count >= 2:
                weaknesses[f"task_{task_type}"] = 1.0 - (count * 0.2)
        
        # Добавляем в очередь улучшений
        for weakness_name, severity in weaknesses.items():
            if severity < 0.7:
                self.skill_improvement_queue.append(weakness_name)
        
        self.weakness_detection.update(weaknesses)
        
        return {
            "weaknesses_detected": len(weaknesses),
            "improvement_queue": self.skill_improvement_queue[:5],
            "suggested_focus": list(weaknesses.keys())[:3],
        }

    async def create_improvement_plan(
        self,
        weakness: str,
        available_time_hours: int = 24,
    ) -> Dict[str, Any]:
        """Создать план улучшения конкретного навыка"""
        
        plan = {
            "weakness": weakness,
            "steps": [
                "Analyze failure patterns",
                "Research solutions",
                "Implement fix",
                "Test thoroughly",
                "Extract as reusable skill",
            ],
            "estimated_duration_hours": available_time_hours,
            "priority": "high",
            "created_at": datetime.now().isoformat(),
        }
        
        # Установить цель для этого плана
        await self.set_goal(
            goal_id=f"improve_{weakness}",
            description=f"Improve weakness: {weakness}",
            priority=GoalPriority.HIGH,
            deadline_hours=available_time_hours,
        )
        
        return plan

    async def auto_initiate_improvement(
        self,
        critic_feedback: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Автоматически инициировать улучшения на основе критики"""
        
        improvement_triggered = False
        
        # Если есть паттерн ошибок
        if not critic_feedback.get("success") and critic_feedback.get("confidence", 0) > 0.8:
            improvements = critic_feedback.get("improvements", [])
            for improvement in improvements:
                # Автоматически добавляем в очередь
                self.skill_improvement_queue.append(improvement)
                improvement_triggered = True
        
        return {
            "auto_improvement": improvement_triggered,
            "improvement_queue_size": len(self.skill_improvement_queue),
        }

    async def get_strategic_status(self) -> Dict[str, Any]:
        """Статус стратегии"""
        
        active_goals = [g for g in self.goals.values() if g.status == GoalStatus.ACTIVE]
        completed_goals = [g for g in self.goals.values() if g.status == GoalStatus.COMPLETED]
        
        return {
            "active_goals": len(active_goals),
            "completed_goals": len(completed_goals),
            "weaknesses": len(self.weakness_detection),
            "improvement_queue_size": len(self.skill_improvement_queue),
            "strategy_iterations": self.strategy_iterations,
            "next_improvement_targets": self.skill_improvement_queue[:3],
        }
