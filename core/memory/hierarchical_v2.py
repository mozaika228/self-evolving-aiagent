from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
import json
import uuid

try:
    import redis
except Exception:  # pragma: no cover - optional dependency
    redis = None

from core.memory.embedder import Embedder


class MemoryType(Enum):
    SHORT_TERM = "short_term"
    WORKING = "working"
    LONG_TERM = "long_term"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    SKILL = "skill"


@dataclass
class MemoryVersion:
    version_id: str
    timestamp: str
    content: Any
    confidence: float
    reason: str = "update"


@dataclass
class MemoryEntry:
    entry_id: str
    content: Any
    memory_type: MemoryType
    timestamp: str
    importance: float
    confidence: float = 0.7
    usage_count: int = 0
    success_rate: float = 1.0
    last_accessed: str = ""
    ttl_seconds: Optional[int] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    versions: List[MemoryVersion] = field(default_factory=list)

    def is_expired(self) -> bool:
        if not self.ttl_seconds:
            return False
        created = datetime.fromisoformat(self.timestamp)
        return datetime.now() - created > timedelta(seconds=self.ttl_seconds)

    def update_access(self) -> None:
        self.usage_count += 1
        self.last_accessed = datetime.now().isoformat()

    def decay_confidence(self, half_life_days: int = 14) -> None:
        age_days = max(0, (datetime.now() - datetime.fromisoformat(self.timestamp)).days)
        if age_days == 0:
            return
        decay_factor = 0.5 ** (age_days / float(half_life_days))
        self.confidence = max(0.01, min(1.0, self.confidence * decay_factor))

    def add_version(self, content: Any, confidence: float, reason: str) -> MemoryVersion:
        version = MemoryVersion(
            version_id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            content=content,
            confidence=confidence,
            reason=reason,
        )
        self.versions.append(version)
        self.content = content
        self.confidence = max(0.01, min(1.0, confidence))
        return version


class HierarchicalMemorySystem:
    """Memory v3: unified graph + consolidation + forgetting + versioning."""

    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379):
        self.redis_client = (
            redis.Redis(host=redis_host, port=redis_port, decode_responses=True) if redis else None
        )
        self.embedder = Embedder()
        self.memory_layers: Dict[MemoryType, List[MemoryEntry]] = {mtype: [] for mtype in MemoryType}
        self.entry_index: Dict[str, MemoryEntry] = {}
        self.graph_links: Dict[str, List[Dict[str, Any]]] = {}
        self.consolidation_threshold = 0.7

    async def store(
        self,
        content: Any,
        memory_type: MemoryType,
        importance: float = 0.5,
        ttl_seconds: Optional[int] = None,
        confidence: float = 0.7,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        entry = MemoryEntry(
            entry_id=str(uuid.uuid4()),
            content=content,
            memory_type=memory_type,
            timestamp=datetime.now().isoformat(),
            importance=max(0.0, min(1.0, importance)),
            confidence=max(0.01, min(1.0, confidence)),
            ttl_seconds=ttl_seconds or self._default_ttl(memory_type),
            tags=tags or [],
            metadata=metadata or {},
        )
        entry.add_version(content=content, confidence=entry.confidence, reason="create")

        self.memory_layers[memory_type].append(entry)
        self.entry_index[entry.entry_id] = entry
        self.graph_links.setdefault(entry.entry_id, [])

        await self._persist_entry(entry)
        return entry.entry_id

    async def retrieve(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        top_k: int = 5,
    ) -> List[MemoryEntry]:
        query_embedding = self.embedder.embed(query)
        candidates: List[tuple[MemoryEntry, float]] = []
        types_to_search = [memory_type] if memory_type else list(MemoryType)

        for mtype in types_to_search:
            for entry in self.memory_layers[mtype]:
                if entry.is_expired():
                    continue
                content_embedding = self.embedder.embed(str(entry.content)[:500])
                similarity = self.embedder.similarity(query_embedding, content_embedding)
                score = similarity * (0.6 * entry.importance + 0.4 * entry.confidence) * (1 + entry.usage_count * 0.05)
                candidates.append((entry, score))

        candidates.sort(key=lambda x: x[1], reverse=True)
        results = [entry for entry, _ in candidates[:top_k]]
        for entry in results:
            entry.update_access()
        return results

    async def link_entries(
        self,
        source_id: str,
        target_id: str,
        relation: str,
        weight: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        if source_id not in self.entry_index or target_id not in self.entry_index:
            return False
        link = {
            "target_id": target_id,
            "relation": relation,
            "weight": max(0.0, min(1.0, weight)),
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }
        self.graph_links.setdefault(source_id, []).append(link)
        await self._persist_links(source_id)
        return True

    async def update_entry(
        self,
        entry_id: str,
        new_content: Any,
        confidence: Optional[float] = None,
        reason: str = "update",
    ) -> Optional[str]:
        entry = self.entry_index.get(entry_id)
        if not entry:
            return None
        version = entry.add_version(
            content=new_content,
            confidence=confidence if confidence is not None else entry.confidence,
            reason=reason,
        )
        await self._persist_entry(entry)
        return version.version_id

    async def rollback_entry(self, entry_id: str, version_id: str) -> bool:
        entry = self.entry_index.get(entry_id)
        if not entry:
            return False
        target = next((v for v in entry.versions if v.version_id == version_id), None)
        if not target:
            return False
        entry.add_version(content=target.content, confidence=target.confidence, reason=f"rollback:{version_id}")
        await self._persist_entry(entry)
        return True

    async def consolidate_memory(self) -> Dict[str, Any]:
        promoted = 0
        for entry in list(self.memory_layers[MemoryType.WORKING]):
            if entry.usage_count >= 3 and entry.success_rate >= self.consolidation_threshold:
                self.memory_layers[MemoryType.WORKING].remove(entry)
                entry.memory_type = MemoryType.LONG_TERM
                self.memory_layers[MemoryType.LONG_TERM].append(entry)
                promoted += 1

        dedup = await self.merge_similar_patterns()
        return {"promoted": promoted, **dedup}

    async def nightly_maintenance(self) -> Dict[str, Any]:
        consolidation = await self.consolidate_memory()
        forgetting = await self.natural_forgetting()
        return {
            "timestamp": datetime.now().isoformat(),
            "consolidation": consolidation,
            "forgetting": forgetting,
            "total_entries": len(self.entry_index),
        }

    async def natural_forgetting(self) -> Dict[str, Any]:
        removed = 0
        decayed = 0
        for mtype in MemoryType:
            kept: List[MemoryEntry] = []
            for entry in self.memory_layers[mtype]:
                entry.decay_confidence()
                decayed += 1
                if entry.is_expired():
                    removed += 1
                    self.entry_index.pop(entry.entry_id, None)
                    self.graph_links.pop(entry.entry_id, None)
                    continue

                threshold = 0.08 if mtype in (MemoryType.SKILL, MemoryType.SEMANTIC) else 0.15
                if (entry.importance * entry.confidence) < threshold and entry.usage_count < 2:
                    removed += 1
                    self.entry_index.pop(entry.entry_id, None)
                    self.graph_links.pop(entry.entry_id, None)
                else:
                    kept.append(entry)
            self.memory_layers[mtype] = kept
        return {"removed_entries": removed, "decayed_entries": decayed}

    async def merge_similar_patterns(self) -> Dict[str, Any]:
        merged = 0
        for mtype in (MemoryType.SEMANTIC, MemoryType.SKILL, MemoryType.LONG_TERM):
            entries = self.memory_layers[mtype]
            i = 0
            while i < len(entries):
                base = entries[i]
                j = i + 1
                while j < len(entries):
                    candidate = entries[j]
                    sim = self.embedder.similarity(
                        self.embedder.embed(str(base.content)[:300]),
                        self.embedder.embed(str(candidate.content)[:300]),
                    )
                    if sim > 0.9:
                        base.importance = max(base.importance, candidate.importance)
                        base.confidence = max(base.confidence, candidate.confidence)
                        base.usage_count += candidate.usage_count
                        base.tags = list(set(base.tags + candidate.tags))
                        await self.link_entries(base.entry_id, candidate.entry_id, relation="merged_from", weight=sim)
                        entries.pop(j)
                        self.entry_index.pop(candidate.entry_id, None)
                        merged += 1
                    else:
                        j += 1
                i += 1
        return {"merged_patterns": merged}

    async def get_memory_stats(self) -> Dict[str, Any]:
        layers = {}
        for mtype in MemoryType:
            entries = [e for e in self.memory_layers[mtype] if not e.is_expired()]
            layers[mtype.value] = {
                "count": len(entries),
                "avg_importance": sum(e.importance for e in entries) / len(entries) if entries else 0.0,
                "avg_confidence": sum(e.confidence for e in entries) / len(entries) if entries else 0.0,
            }
        total_links = sum(len(v) for v in self.graph_links.values())
        return {
            "layers": layers,
            "total_entries": len(self.entry_index),
            "total_links": total_links,
        }

    async def get_entry_history(self, entry_id: str) -> List[Dict[str, Any]]:
        entry = self.entry_index.get(entry_id)
        if not entry:
            return []
        return [
            {
                "version_id": version.version_id,
                "timestamp": version.timestamp,
                "confidence": version.confidence,
                "reason": version.reason,
            }
            for version in entry.versions
        ]

    def _default_ttl(self, memory_type: MemoryType) -> Optional[int]:
        ttl_map = {
            MemoryType.SHORT_TERM: 7200,
            MemoryType.WORKING: 28800,
            MemoryType.LONG_TERM: 86400 * 30,
            MemoryType.EPISODIC: 86400 * 2,
            MemoryType.SEMANTIC: None,
            MemoryType.SKILL: None,
        }
        return ttl_map.get(memory_type)

    async def _persist_entry(self, entry: MemoryEntry) -> None:
        if not self.redis_client:
            return
        payload = {
            "entry_id": entry.entry_id,
            "content": str(entry.content),
            "memory_type": entry.memory_type.value,
            "timestamp": entry.timestamp,
            "importance": entry.importance,
            "confidence": entry.confidence,
            "usage_count": entry.usage_count,
            "success_rate": entry.success_rate,
            "last_accessed": entry.last_accessed,
            "ttl_seconds": entry.ttl_seconds,
            "tags": entry.tags,
            "metadata": entry.metadata,
            "versions": [v.__dict__ for v in entry.versions],
        }
        ttl = entry.ttl_seconds if entry.ttl_seconds else 86400 * 365
        self.redis_client.setex(f"memory:v3:entry:{entry.entry_id}", ttl, json.dumps(payload))

    async def _persist_links(self, source_id: str) -> None:
        if not self.redis_client:
            return
        links = self.graph_links.get(source_id, [])
        self.redis_client.set(f"memory:v3:links:{source_id}", json.dumps(links))
