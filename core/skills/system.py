from typing import Dict, Any, Callable
from dataclasses import dataclass
import inspect
import hashlib
from datetime import datetime


@dataclass
class Skill:
    name: str
    func: Callable
    context: str
    success_rate: float
    usage_count: int
    created_at: str
    last_used: str
    code: str

    def execute(self, *args, **kwargs) -> Any:
        self.usage_count += 1
        self.last_used = datetime.now().isoformat()
        return self.func(*args, **kwargs)

    def get_signature(self) -> str:
        return hashlib.md5(self.code.encode()).hexdigest()


class SkillSystem:
    def __init__(self):
        self.skills: Dict[str, Skill] = {}
        self.skill_graph: Dict[str, list] = {}

    async def extract_skill(
        self,
        task: str,
        code: str,
        test_score: float,
        dependencies: list = None,
    ) -> Skill:
        skill_name = self._generate_skill_name(task)
        
        func = self._compile_skill(code)
        
        skill = Skill(
            name=skill_name,
            func=func,
            context=task,
            success_rate=test_score,
            usage_count=0,
            created_at=datetime.now().isoformat(),
            last_used=datetime.now().isoformat(),
            code=code,
        )
        
        self.skills[skill_name] = skill
        
        if dependencies:
            self.skill_graph[skill_name] = dependencies
        else:
            self.skill_graph[skill_name] = []
        
        return skill

    async def compose_skills(self, skill_names: list) -> Callable:
        skills = [self.skills[name] for name in skill_names if name in self.skills]
        
        async def composed(*args, **kwargs):
            result = args[0] if args else kwargs
            for skill in skills:
                result = skill.execute(result)
            return result
        
        return composed

    async def get_relevant_skills(
        self,
        task: str,
        limit: int = 5,
    ) -> list:
        from core.memory.embedder import Embedder
        
        embedder = Embedder()
        task_embedding = embedder.embed(task)
        
        skill_scores = []
        for name, skill in self.skills.items():
            skill_embedding = embedder.embed(skill.context)
            similarity = embedder.similarity(task_embedding, skill_embedding)
            skill_scores.append((name, similarity * skill.success_rate))
        
        skill_scores.sort(key=lambda x: x[1], reverse=True)
        return [name for name, _ in skill_scores[:limit]]

    def _generate_skill_name(self, task: str) -> str:
        import re
        cleaned = re.sub(r'[^a-z0-9]', '_', task.lower())[:30]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"skill_{cleaned}_{timestamp}"

    def _compile_skill(self, code: str) -> Callable:
        namespace = {}
        exec(code, namespace)
        
        for name, obj in namespace.items():
            if callable(obj) and not name.startswith('_'):
                return obj
        
        raise ValueError("No callable function found in code")

    async def get_statistics(self) -> Dict[str, Any]:
        return {
            "total_skills": len(self.skills),
            "avg_success_rate": sum(s.success_rate for s in self.skills.values()) / len(self.skills) if self.skills else 0,
            "total_usage": sum(s.usage_count for s in self.skills.values()),
            "most_used": max(
                ((name, skill.usage_count) for name, skill in self.skills.items()),
                key=lambda x: x[1],
                default=(None, 0),
            )[0],
        }
