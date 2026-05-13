from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class StructuralChangeType(Enum):
    NEW_TOOL = "new_tool"
    NEW_PIPELINE = "new_pipeline"
    NEW_HEURISTIC = "new_heuristic"
    OPTIMIZED_FLOW = "optimized_flow"


class ToolStatus(Enum):
    PENDING_APPROVAL = "pending_approval"
    ACTIVE = "active"
    DISABLED = "disabled"


@dataclass
class StructuralChange:
    change_type: StructuralChangeType
    description: str
    implementation: str
    triggered_by_patterns: List[str]
    efficiency_gain: float
    timestamp: str


@dataclass
class ToolRecord:
    name: str
    pattern_steps: List[str]
    code: str
    tests: List[str]
    benchmark: Dict[str, float]
    status: ToolStatus
    approval: Dict[str, Any]
    rating: float
    usage_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    last_score: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class StructuralEvolution:
    """Structural Evolution Engine v2: miner + synthesis + registry lifecycle."""

    def __init__(self):
        self.custom_tools: Dict[str, Callable] = {}
        self.pipelines: Dict[str, List[str]] = {}
        self.heuristics: Dict[str, Callable] = {}
        self.changes_history: List[StructuralChange] = []
        self.pattern_detection_threshold = 3
        self.tool_registry: Dict[str, ToolRecord] = {}
        self.disable_threshold = 0.45

    async def detect_repeating_patterns(self, task_history: List[Dict]) -> List[Dict]:
        patterns: Dict[tuple, Dict[str, Any]] = {}
        for task in task_history[-50:]:
            steps = task.get("steps", [])
            if not steps:
                continue
            steps_key = tuple(steps)
            current = patterns.setdefault(
                steps_key,
                {
                    "count": 0,
                    "steps": steps,
                    "scores": [],
                    "times": [],
                    "successes": 0,
                },
            )
            current["count"] += 1
            if "score" in task:
                current["scores"].append(task.get("score", 0.0))
            if "time" in task:
                current["times"].append(task.get("time", 0.0))
            if task.get("success"):
                current["successes"] += 1

        frequent_patterns = []
        for data in patterns.values():
            if data["count"] < self.pattern_detection_threshold:
                continue
            avg_score = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0.0
            avg_time = sum(data["times"]) / len(data["times"]) if data["times"] else 0.0
            success_rate = data["successes"] / data["count"]
            frequent_patterns.append(
                {
                    "pattern": data["steps"],
                    "frequency": data["count"],
                    "avg_score": round(avg_score, 4),
                    "avg_time": round(avg_time, 4),
                    "success_rate": round(success_rate, 4),
                    "priority": round((data["count"] * success_rate) + avg_score, 4),
                }
            )

        return sorted(frequent_patterns, key=lambda x: x["priority"], reverse=True)

    async def create_custom_tool(self, pattern_steps: List[str], pattern_name: str) -> Dict[str, Any]:
        synthesis = await self._synthesize_tool(pattern_steps, pattern_name)
        tests = self._generate_tool_tests(pattern_name, pattern_steps)
        benchmark = self._run_synthetic_benchmark(pattern_steps)
        approval = self._request_sandbox_approval(pattern_name, pattern_steps, benchmark)

        status = ToolStatus.ACTIVE if approval["approved"] else ToolStatus.PENDING_APPROVAL
        rating = self._compute_initial_rating(benchmark, approval["approved"])

        record = ToolRecord(
            name=pattern_name,
            pattern_steps=pattern_steps,
            code=synthesis,
            tests=tests,
            benchmark=benchmark,
            status=status,
            approval=approval,
            rating=rating,
            last_score=rating,
        )
        self.tool_registry[pattern_name] = record

        if status == ToolStatus.ACTIVE:
            self.custom_tools[pattern_name] = self._compile_tool(synthesis)

        change = StructuralChange(
            change_type=StructuralChangeType.NEW_TOOL,
            description=f"Auto-synthesized tool: {pattern_name}",
            implementation=synthesis,
            triggered_by_patterns=pattern_steps,
            efficiency_gain=benchmark.get("efficiency_gain", 0.0),
            timestamp=datetime.now().isoformat(),
        )
        self.changes_history.append(change)

        return {
            "tool_name": pattern_name,
            "status": status.value,
            "benchmark": benchmark,
            "approval": approval,
            "rating": rating,
        }

    async def create_pipeline(self, steps: List[str], pipeline_name: str) -> Dict[str, Any]:
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
        return {"pipeline_name": pipeline_name, "steps": steps, "status": "created"}

    async def add_heuristic(self, name: str, condition: Callable, action: Callable):
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

    async def update_tool_outcome(self, tool_name: str, success: bool, score: float) -> Dict[str, Any]:
        record = self.tool_registry.get(tool_name)
        if not record:
            return {"updated": False, "reason": "tool_not_found"}

        record.usage_count += 1
        if success:
            record.success_count += 1
        else:
            record.failure_count += 1

        success_rate = record.success_count / max(1, record.usage_count)
        record.last_score = score
        record.rating = round(0.6 * success_rate + 0.4 * max(0.0, min(1.0, score)), 4)
        record.updated_at = datetime.now().isoformat()

        if record.usage_count >= 5 and record.rating < self.disable_threshold:
            record.status = ToolStatus.DISABLED
            self.custom_tools.pop(tool_name, None)

        return {
            "updated": True,
            "tool_name": tool_name,
            "status": record.status.value,
            "rating": record.rating,
            "success_rate": round(success_rate, 4),
        }

    async def approve_tool(self, tool_name: str, approved: bool, approver: str = "system") -> Dict[str, Any]:
        record = self.tool_registry.get(tool_name)
        if not record:
            return {"approved": False, "reason": "tool_not_found"}

        record.approval.update(
            {
                "approved": approved,
                "approver": approver,
                "approved_at": datetime.now().isoformat(),
            }
        )
        record.status = ToolStatus.ACTIVE if approved else ToolStatus.DISABLED
        if approved:
            self.custom_tools[tool_name] = self._compile_tool(record.code)
        else:
            self.custom_tools.pop(tool_name, None)
        record.updated_at = datetime.now().isoformat()

        return {"approved": approved, "tool_name": tool_name, "status": record.status.value}

    async def get_registry_report(self) -> Dict[str, Any]:
        active = [r for r in self.tool_registry.values() if r.status == ToolStatus.ACTIVE]
        disabled = [r for r in self.tool_registry.values() if r.status == ToolStatus.DISABLED]
        pending = [r for r in self.tool_registry.values() if r.status == ToolStatus.PENDING_APPROVAL]

        return {
            "total_tools": len(self.tool_registry),
            "active": len(active),
            "disabled": len(disabled),
            "pending_approval": len(pending),
            "top_rated": [
                {
                    "name": r.name,
                    "rating": r.rating,
                    "status": r.status.value,
                }
                for r in sorted(self.tool_registry.values(), key=lambda x: x.rating, reverse=True)[:10]
            ],
        }

    def _compile_tool(self, code: str) -> Callable:
        namespace: Dict[str, Any] = {}
        exec(code, namespace)
        for name, obj in namespace.items():
            if callable(obj) and not name.startswith("_"):
                return obj
        raise ValueError("No callable found")

    async def _synthesize_tool(self, pattern_steps: List[str], pattern_name: str) -> str:
        return f'''async def {pattern_name}(context):
    """Auto-synthesized tool.

    Pattern: {' -> '.join(pattern_steps)}
    """
    state = context
    # pipeline skeleton generated from execution traces
    for _step in {pattern_steps!r}:
        state = state
    return state
'''

    def _generate_tool_tests(self, pattern_name: str, pattern_steps: List[str]) -> List[str]:
        return [
            f"test_{pattern_name}_returns_context",
            f"test_{pattern_name}_handles_empty_steps",
            f"test_{pattern_name}_is_async_callable",
        ]

    def _run_synthetic_benchmark(self, pattern_steps: List[str]) -> Dict[str, float]:
        step_count = max(1, len(pattern_steps))
        baseline_latency = 1.0 * step_count
        optimized_latency = max(0.3, baseline_latency * 0.78)
        efficiency_gain = max(0.0, 1.0 - (optimized_latency / baseline_latency))
        reliability = min(0.98, 0.7 + (0.03 * step_count))
        return {
            "baseline_latency": round(baseline_latency, 4),
            "optimized_latency": round(optimized_latency, 4),
            "efficiency_gain": round(efficiency_gain, 4),
            "reliability": round(reliability, 4),
        }

    def _request_sandbox_approval(
        self,
        tool_name: str,
        pattern_steps: List[str],
        benchmark: Dict[str, float],
    ) -> Dict[str, Any]:
        safe_steps = {"retrieve", "execute", "review", "store", "improve", "analyze", "validate"}
        risky = [step for step in pattern_steps if step not in safe_steps]
        approved = len(risky) == 0 and benchmark.get("reliability", 0.0) >= 0.72
        return {
            "approved": approved,
            "mode": "auto" if approved else "manual_required",
            "risky_steps": risky,
            "reason": "contains_untrusted_steps" if risky else "passes_policy",
        }

    def _compute_initial_rating(self, benchmark: Dict[str, float], approved: bool) -> float:
        base = 0.5 * benchmark.get("efficiency_gain", 0.0) + 0.5 * benchmark.get("reliability", 0.0)
        if not approved:
            base *= 0.6
        return round(max(0.0, min(1.0, base)), 4)

    async def get_evolution_report(self) -> Dict[str, Any]:
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
            "registry": await self.get_registry_report(),
        }
