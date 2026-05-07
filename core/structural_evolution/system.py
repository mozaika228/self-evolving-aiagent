from typing import Dict, Any, List, Callable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class StructuralChangeType(Enum):
    NEW_TOOL = "new_tool"
    NEW_PIPELINE = "new_pipeline"
    NEW_HEURISTIC = "new_heuristic"
    OPTIMIZED_FLOW = "optimized_flow"


@dataclass
class StructuralChange:
    change_type: StructuralChangeType
    description: str
    implementation: str
    triggered_by_patterns: List[str]
    efficiency_gain: float  # 0.0-1.0
    timestamp: str


class StructuralEvolution:
    """Изменение собственной архитектуры агента"""
    
    def __init__(self):
        self.custom_tools: Dict[str, Callable] = {}
        self.pipelines: Dict[str, List[str]] = {}
        self.heuristics: Dict[str, Callable] = {}
        self.changes_history: List[StructuralChange] = []
        self.pattern_detection_threshold = 3  # Минимум повторений для детекции

    async def detect_repeating_patterns(self, task_history: List[Dict]) -> List[Dict]:
        """Обнаружить повторяющиеся последовательности"""
        patterns = {}
        
        # Анализируем последние задачи
        for i, task in enumerate(task_history[-20:]):
            steps = task.get("steps", [])
            steps_key = tuple(steps)  # Используем как ключ
            
            if steps_key in patterns:
                patterns[steps_key]["count"] += 1
            else:
                patterns[steps_key] = {
                    "count": 1,
                    "steps": steps,
                    "efficiency": task.get("efficiency", 0.5),
                }
        
        # Отфильтровываем часто встречающиеся
        frequent_patterns = [
            {"pattern": steps, "frequency": data["count"], "efficiency": data["efficiency"]}
            for steps, data in patterns.items()
            if data["count"] >= self.pattern_detection_threshold
        ]
        
        return sorted(frequent_patterns, key=lambda x: x["frequency"], reverse=True)

    async def create_custom_tool(
        self,
        pattern_steps: List[str],
        pattern_name: str,
    ) -> Dict[str, Any]:
        """Создать кастомный tool из паттерна"""
        
        tool_code = f"""
async def {pattern_name}(context):
    \"\"\"Auto-generated tool from pattern detection\"\"\"
    # Implements: {' -> '.join(pattern_steps)}
    result = context
    # Sequential execution of detected pattern
    return result
"""
        
        self.custom_tools[pattern_name] = self._compile_tool(tool_code)
        
        change = StructuralChange(
            change_type=StructuralChangeType.NEW_TOOL,
            description=f"Auto-generated tool: {pattern_name}",
            implementation=tool_code,
            triggered_by_patterns=pattern_steps,
            efficiency_gain=0.15,  # Оценка улучшения
            timestamp=datetime.now().isoformat(),
        )
        
        self.changes_history.append(change)
        
        return {
            "tool_name": pattern_name,
            "status": "created",
            "efficiency_expected": 0.15,
        }

    async def create_pipeline(
        self,
        steps: List[str],
        pipeline_name: str,
    ) -> Dict[str, Any]:
        """Создать pipeline из последовательности шагов"""
        
        self.pipelines[pipeline_name] = steps
        
        change = StructuralChange(
            change_type=StructuralChangeType.NEW_PIPELINE,
            description=f"Pipeline: {pipeline_name}",
            implementation=str(steps),
            triggered_by_patterns=steps,
            efficiency_gain=0.2,
            timestamp=datetime.now().isoformat(),
        )
        
        self.changes_history.append(change)
        
        return {
            "pipeline_name": pipeline_name,
            "steps": steps,
            "status": "created",
        }

    async def add_heuristic(
        self,
        name: str,
        condition: Callable,
        action: Callable,
    ):
        """Добавить эвристику для автоматизации решений"""
        
        async def heuristic_wrapper(context):
            if await condition(context):
                return await action(context)
            return None
        
        self.heuristics[name] = heuristic_wrapper
        
        change = StructuralChange(
            change_type=StructuralChangeType.NEW_HEURISTIC,
            description=f"Heuristic: {name}",
            implementation=str(condition) + " -> " + str(action),
            triggered_by_patterns=[],
            efficiency_gain=0.1,
            timestamp=datetime.now().isoformat(),
        )
        
        self.changes_history.append(change)

    def _compile_tool(self, code: str) -> Callable:
        """Скомпилировать tool из кода"""
        namespace = {}
        exec(code, namespace)
        
        for name, obj in namespace.items():
            if callable(obj) and not name.startswith('_'):
                return obj
        
        raise ValueError("No callable found")

    async def get_evolution_report(self) -> Dict[str, Any]:
        """Отчёт об эволюции структуры"""
        return {
            "custom_tools_count": len(self.custom_tools),
            "pipelines_count": len(self.pipelines),
            "heuristics_count": len(self.heuristics),
            "total_efficiency_gain": sum(c.efficiency_gain for c in self.changes_history),
            "changes_history": [
                {
                    "type": c.change_type.value,
                    "description": c.description,
                    "timestamp": c.timestamp,
                    "efficiency_gain": c.efficiency_gain,
                }
                for c in self.changes_history[-20:]
            ],
        }
