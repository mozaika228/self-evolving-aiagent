import json
from typing import Dict, List, Any
from datetime import datetime

try:
    import redis
except Exception:  # pragma: no cover - optional dependency
    redis = None


class RLTrainer:
    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        buffer_size: int = 10000,
    ):
        self.redis_client = (
            redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
            if redis
            else None
        )
        self._buffer: List[str] = []
        self._kv_store: Dict[str, str] = {}
        self.buffer_size = buffer_size
        self.policy_version = 0

    async def add_experience(
        self,
        task: str,
        code: str,
        reward: float,
        score: float,
    ) -> None:
        experience = {
            "task": task,
            "code": code,
            "reward": reward,
            "score": score,
            "timestamp": datetime.now().isoformat(),
        }

        encoded = json.dumps(experience)
        if self.redis_client:
            self.redis_client.lpush("experience_buffer", encoded)
            self.redis_client.ltrim("experience_buffer", 0, self.buffer_size - 1)
        else:
            self._buffer.insert(0, encoded)
            self._buffer = self._buffer[: self.buffer_size]

    async def update_policy(self, patterns: List[Dict[str, Any]], stats: Dict[str, Any]) -> Dict[str, Any]:
        self.policy_version += 1
        
        avg_reward = stats.get("avg_reward", 0.0)
        
        policy = {
            "version": self.policy_version,
            "patterns_count": len(patterns),
            "avg_reward": avg_reward,
            "timestamp": datetime.now().isoformat(),
        }

        if self.redis_client:
            self.redis_client.set(f"policy:v{self.policy_version}", json.dumps(policy))
            self.redis_client.set("current_policy_version", str(self.policy_version))
        else:
            self._kv_store[f"policy:v{self.policy_version}"] = json.dumps(policy)
            self._kv_store["current_policy_version"] = str(self.policy_version)

        return policy

    async def get_batch(
        self,
        batch_size: int = 32,
    ) -> List[Dict[str, Any]]:
        if self.redis_client:
            experiences = self.redis_client.lrange("experience_buffer", 0, batch_size - 1)
        else:
            experiences = self._buffer[:batch_size]
        return [json.loads(exp) for exp in experiences]

    async def get_policy_stats(self) -> Dict[str, Any]:
        if self.redis_client:
            version = self.redis_client.get("current_policy_version")
        else:
            version = self._kv_store.get("current_policy_version")
        if not version:
            return {"version": 0, "status": "no_policy"}

        if self.redis_client:
            policy = self.redis_client.get(f"policy:v{version}")
        else:
            policy = self._kv_store.get(f"policy:v{version}")
        return json.loads(policy) if policy else {}
