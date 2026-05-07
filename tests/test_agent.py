import pytest
import asyncio
from core.agent import EvolvingAgent
from core.llm_engine import LLMEngine
from core.executor import CodeExecutor
from core.memory.embedder import Embedder


@pytest.fixture
async def agent():
    return EvolvingAgent()


def test_executor_python():
    executor = CodeExecutor()
    code = 'print("Hello, World!")'
    result = asyncio.run(executor.execute(code, language="python"))
    if result["returncode"] != 0 and result.get("error") and "WinError 5" in result["error"]:
        pytest.skip("Execution is blocked by environment permissions")
    assert result["returncode"] == 0
    assert "Hello, World!" in result["output"]


def test_executor_error():
    executor = CodeExecutor()
    code = "raise ValueError('Test error')"
    result = asyncio.run(executor.execute(code, language="python"))
    assert result["returncode"] != 0
    assert result["error"] is not None


def test_embedder():
    embedder = Embedder()
    text1 = "The quick brown fox"
    text2 = "A fast brown fox"
    
    emb1 = embedder.embed(text1)
    emb2 = embedder.embed(text2)
    
    assert len(emb1) == 384
    assert len(emb2) == 384
    
    similarity = embedder.similarity(emb1, emb2)
    assert 0 <= similarity <= 1
    assert similarity > 0.7


def test_llm_health():
    llm = LLMEngine()
    health = asyncio.run(llm.check_health())
    assert isinstance(health, bool)


def test_agent_execute():
    agent = EvolvingAgent(max_iterations=2)
    result = asyncio.run(
        agent.execute(
            "Write a function that returns the sum of two numbers",
            language="python",
            learn=False,
        )
    )
    assert isinstance(result.code, str)
    assert result.iterations >= 1
    assert result.total_time > 0


def test_reward_model():
    from core.rl.reward_model import RewardModel
    
    model = RewardModel()
    reward = model.calculate(
        test_score=0.9,
        iterations=2,
        code_quality=0.85,
    )
    
    assert 0.0 <= reward <= 1.0
    assert reward > 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
