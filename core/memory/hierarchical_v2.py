from typing import Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json
import redis


class MemoryType(Enum):
    SHORT_TERM = "short_term"      # Текущая задача (1-2 часа)
    WORKING = "working"             # Рабочая память (сессия)
    LONG_TERM = "long_term"         # Знания (недели)
    EPISODIC = "episodic"           # События (1-2 дня)
    SEMANTIC = "semantic"           # Факты, правила
    SKILL = "skill"                 # Переиспользуемые способности


@dataclass
class MemoryEntry:
    content: Any
    memory_type: MemoryType
    timestamp: str
    importance: float  # 0.0-1.0
    usage_count: int = 0
    success_rate: float = 1.0
    last_accessed: str = ""
    ttl_seconds: int = None
    
    def is_expired(self) -> bool:
        if not self.ttl_seconds:
            return False
        created = datetime.fromisoformat(self.timestamp)
        return datetime.now() - created > timedelta(seconds=self.ttl_seconds)
    
    def update_access(self):
        self.usage_count += 1
        self.last_accessed = datetime.now().isoformat()
    
    def decay_importance(self, decay_rate: float = 0.95):
        """Естественное затухание неиспользуемых знаний"""
        days_old = (datetime.now() - datetime.fromisoformat(self.timestamp)).days
        self.importance *= (decay_rate ** days_old)


class HierarchicalMemorySystem:
    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379):
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            decode_responses=True,
        )
        self.memory_layers: Dict[MemoryType, List[MemoryEntry]] = {
            mtype: [] for mtype in MemoryType
        }
        self.consolidation_threshold = 0.7  # Порог для перевода в долгосрочную

    async def store(
        self,
        content: Any,
        memory_type: MemoryType,
        importance: float = 0.5,
        ttl_seconds: int = None,
    ) -> str:
        """Сохранить в иерархию памяти"""
        entry = MemoryEntry(
            content=content,
            memory_type=memory_type,
            timestamp=datetime.now().isoformat(),
            importance=importance,
            ttl_seconds=ttl_seconds,
        )
        
        # TTL по типу памяти
        if not ttl_seconds:
            ttl_map = {
                MemoryType.SHORT_TERM: 3600 * 2,      # 2 часа
                MemoryType.WORKING: 3600 * 8,         # 8 часов
                MemoryType.LONG_TERM: 86400 * 30,     # 30 дней
                MemoryType.EPISODIC: 86400 * 2,       # 2 дня
                MemoryType.SEMANTIC: None,             # Вечно
                MemoryType.SKILL: None,                # Вечно
            }
            entry.ttl_seconds = ttl_map.get(memory_type)
        
        entry_id = self._generate_id()
        self.memory_layers[memory_type].append(entry)
        
        await self._persist_to_redis(entry_id, entry)
        return entry_id

    async def retrieve(
        self,
        query: str,
        memory_type: MemoryType = None,
        top_k: int = 5,
    ) -> List[MemoryEntry]:
        """Получить из памяти (семантический поиск)"""
        from core.memory.embedder import Embedder
        
        embedder = Embedder()
        query_embedding = embedder.embed(query)
        
        candidates = []
        types_to_search = [memory_type] if memory_type else list(MemoryType)
        
        for mtype in types_to_search:
            for entry in self.memory_layers[mtype]:
                if entry.is_expired():
                    continue
                
                content_embedding = embedder.embed(str(entry.content)[:500])
                similarity = embedder.similarity(query_embedding, content_embedding)
                
                # Учитываем важность и историю использования
                score = similarity * entry.importance * (1.0 + entry.usage_count * 0.1)
                candidates.append((entry, score))
        
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Обновляем счётчик доступа
        results = [entry for entry, _ in candidates[:top_k]]
        for entry in results:
            entry.update_access()
        
        return results

    async def consolidate_memory(self) -> Dict[str, Any]:
        """Перевести знания из рабочей памяти в долгосрочную"""
        consolidated = 0
        merged = 0
        
        working_memory = self.memory_layers[MemoryType.WORKING]
        for entry in working_memory:
            # Если успешное использование - переводим в долгосрочную
            if entry.usage_count >= 3 and entry.success_rate > self.consolidation_threshold:
                entry.memory_type = MemoryType.LONG_TERM
                self.memory_layers[MemoryType.LONG_TERM].append(entry)
                consolidated += 1
        
        # Удаляем из рабочей памяти
        self.memory_layers[MemoryType.WORKING] = [
            e for e in working_memory
            if e.memory_type == MemoryType.WORKING
        ]
        
        return {
            "consolidated": consolidated,
            "merged": merged,
        }

    async def natural_forgetting(self) -> Dict[str, Any]:
        """Естественное забывание - удаление малополезного"""
        removed = 0
        
        for mtype in MemoryType:
            entries = self.memory_layers[mtype]
            
            # Применяем decay
            for entry in entries:
                entry.decay_importance()
            
            # Удаляем малоценное
            threshold = 0.1 if mtype != MemoryType.SKILL else 0.05
            self.memory_layers[mtype] = [
                e for e in entries
                if e.importance > threshold or e.memory_type == MemoryType.SKILL
            ]
            removed += len(entries) - len(self.memory_layers[mtype])
        
        return {"removed_entries": removed}

    async def merge_similar_patterns(self) -> Dict[str, Any]:
        """Объединить похожие паттерны"""
        from core.memory.embedder import Embedder
        
        embedder = Embedder()
        merged_count = 0
        
        for mtype in [MemoryType.SEMANTIC, MemoryType.SKILL]:
            entries = self.memory_layers[mtype]
            if len(entries) < 2:
                continue
            
            # Найти похожие
            embeddings = [
                embedder.embed(str(e.content)[:200])
                for e in entries
            ]
            
            clustered = {}
            for i, (entry, emb) in enumerate(zip(entries, embeddings)):
                cluster_id = None
                for existing_id, existing_emb in clustered.items():
                    sim = embedder.similarity(emb, existing_emb)
                    if sim > 0.85:
                        cluster_id = existing_id
                        break
                
                if cluster_id is None:
                    cluster_id = i
                    clustered[cluster_id] = emb
            
            merged_count += len(entries) - len(clustered)
        
        return {"merged_patterns": merged_count}

    async def get_memory_stats(self) -> Dict[str, Any]:
        """Статистика памяти"""
        stats = {}
        total_entries = 0
        total_importance = 0.0
        
        for mtype in MemoryType:
            entries = self.memory_layers[mtype]
            valid_entries = [e for e in entries if not e.is_expired()]
            
            stats[mtype.value] = {
                "count": len(valid_entries),
                "avg_importance": sum(e.importance for e in valid_entries) / len(valid_entries) if valid_entries else 0,
                "total_usage": sum(e.usage_count for e in valid_entries),
            }
            
            total_entries += len(valid_entries)
            total_importance += sum(e.importance for e in valid_entries)
        
        return {
            "layers": stats,
            "total_entries": total_entries,
            "avg_importance": total_importance / total_entries if total_entries else 0,
        }

    async def _persist_to_redis(self, entry_id: str, entry: MemoryEntry):
        """Сохранить в Redis для персистентности"""
        data = {
            "content": str(entry.content),
            "type": entry.memory_type.value,
            "importance": entry.importance,
            "timestamp": entry.timestamp,
            "usage_count": entry.usage_count,
        }
        self.redis_client.setex(
            f"memory:{entry_id}",
            entry.ttl_seconds or 86400 * 365,
            json.dumps(data),
        )

    def _generate_id(self) -> str:
        import uuid
        return str(uuid.uuid4())
