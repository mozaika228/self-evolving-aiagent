# Self-Evolving AI Agent System

AutoGPT/Devin-like system that writes, tests, and improves code autonomously.

## Stack

- **LLM**: Ollama (DeepSeek Coder 7B/33B)
- **Embeddings**: sentence-transformers
- **Vector DB**: Qdrant
- **RL**: Custom reward model + Redis
- **Execution**: Docker sandbox
- **API**: FastAPI
- **Async**: asyncio + aiohttp

## Quick Start

### Docker Compose (Recommended)

```bash
docker-compose up -d
curl http://localhost:8000/docs
```

### Local Setup

```bash
bash start.sh
```

## Features

✨ **Self-Evolution Loop**
- Generate → Test → Analyze → Improve → Learn
- Vector memory for pattern recognition
- Reinforcement learning policy updates
- Self-reflection cycles

🔒 **Secure Code Execution**
- Sandboxed process execution
- Timeout protection
- Resource limits
- Error isolation

🧠 **Memory System**
- Semantic search over solutions
- Pattern extraction
- Quality metrics tracking
- Experience replay buffer

## API Examples

```bash
curl -X POST "http://localhost:8000/api/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Create a factorial function with tests",
    "language": "python",
    "learn": true
  }'
```

## Python SDK

```python
from core.agent import EvolvingAgent

agent = EvolvingAgent(model="deepseek-coder:7b")

result = await agent.execute(
    "Build REST API for TODO management",
    learn=True
)

print(f"Code:\n{result.code}")
print(f"Score: {result.test_score:.1%}")
print(f"Improvement:\n{result.improvement}")
```

## Architecture

```
Agent (self-reflection loop)
├── LLMEngine (Ollama)
├── CodeGenerator (prompt engineering)
├── CodeExecutor (sandbox)
├── TestRunner (pytest metrics)
├── VectorStore (Qdrant)
├── RewardModel (RL)
└── FastAPI Server
```

## Self-Evolution Process

```
Iteration 1: Task → Generate → Test → Score: 60% (FAIL)
Iteration 2: Analyze error → Improve → Score: 80% (FAIL)
Iteration 3: Different approach → Score: 95% (OK)
Iteration 4: Optimize → Score: 100% (PERFECT)

✓ Save to memory
✓ Calculate reward
✓ Update RL policy
✓ Extract patterns
```

## Documentation

- `EXAMPLES.md` - API usage examples
- `ARCHITECTURE.md` - System design

## License

MIT
