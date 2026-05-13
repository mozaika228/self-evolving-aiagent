"""Core package with lazy exports to avoid heavy side-effect imports."""

from __future__ import annotations

from typing import Any

__version__ = "0.1.0"
__all__ = ["EvolvingAgent", "LLMEngine", "CodeExecutor"]


def __getattr__(name: str) -> Any:
    if name == "EvolvingAgent":
        from core.agent import EvolvingAgent
        return EvolvingAgent
    if name == "LLMEngine":
        from core.llm_engine import LLMEngine
        return LLMEngine
    if name == "CodeExecutor":
        from core.executor import CodeExecutor
        return CodeExecutor
    raise AttributeError(f"module 'core' has no attribute {name!r}")
