from typing import Dict, Any, List
from enum import Enum
from dataclasses import dataclass


class MemoryLevel(Enum):
    L0_RAW = "raw_logs"
    L1_INSIGHTS = "insights"
    L2_KNOWLEDGE = "knowledge"
    L3_SKILLS = "skills"
    L4_STRATEGY = "strategy"


@dataclass
class MemoryEntry:
    level: MemoryLevel
    content: Any
    score: float
    timestamp: str
    source: str


class HierarchicalMemory:
    def __init__(self):
        self.levels = {
            MemoryLevel.L0_RAW: [],
            MemoryLevel.L1_INSIGHTS: [],
            MemoryLevel.L2_KNOWLEDGE: [],
            MemoryLevel.L3_SKILLS: [],
            MemoryLevel.L4_STRATEGY: [],
        }

    async def add_entry(self, entry: MemoryEntry) -> None:
        self.levels[entry.level].append(entry)

    async def promote(
        self,
        content: Any,
        from_level: MemoryLevel,
        to_level: MemoryLevel,
        score: float,
    ) -> None:
        if from_level not in self.levels or to_level not in self.levels:
            raise ValueError("Invalid memory level")
        
        from datetime import datetime
        entry = MemoryEntry(
            level=to_level,
            content=content,
            score=score,
            timestamp=datetime.now().isoformat(),
            source=from_level.value,
        )
        await self.add_entry(entry)

    async def get_by_level(self, level: MemoryLevel) -> List[MemoryEntry]:
        return self.levels.get(level, [])

    async def get_top_by_score(
        self,
        level: MemoryLevel,
        limit: int = 5,
    ) -> List[MemoryEntry]:
        entries = self.levels.get(level, [])
        return sorted(entries, key=lambda x: x.score, reverse=True)[:limit]
