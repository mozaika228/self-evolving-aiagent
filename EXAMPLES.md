# API Examples

## Execute Task

```bash
curl -X POST "http://localhost:8000/api/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Create a factorial function with comprehensive tests",
    "language": "python",
    "learn": true
  }'
```

## Improve Code

```bash
curl -X POST "http://localhost:8000/api/improve" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def add(a, b): return a + b",
    "language": "python"
  }'
```

## Search Memory

```bash
curl -X POST "http://localhost:8000/api/memory/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "API REST endpoints",
    "limit": 5
  }'
```

## Get Metrics

```bash
curl -X GET "http://localhost:8000/api/metrics"
```

## Reflect and Improve

```bash
curl -X POST "http://localhost:8000/api/reflect" \
  -H "Content-Type: application/json" \
  -d '{
    "auto_update": true
  }'
```

## Generate Code Only

```bash
curl -X POST "http://localhost:8000/api/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Sort array using merge sort algorithm",
    "language": "python"
  }'
```

## Python SDK Examples

```python
import asyncio
from core.agent import EvolvingAgent

async def main():
    agent = EvolvingAgent()
    
    result = await agent.execute(
        "Build a REST API with FastAPI",
        language="python",
        learn=True
    )
    
    print(f"Code:\n{result.code}")
    print(f"Test Score: {result.test_score:.1%}")
    print(f"Iterations: {result.iterations}")
    print(f"Time: {result.total_time:.2f}s")

asyncio.run(main())
```

## Search Similar Solutions

```python
similar = await agent.vector_store.search(
    "Sort array efficiently",
    limit=3
)

for solution in similar:
    print(f"Score: {solution['score']:.2%}")
    print(f"Code:\n{solution['code']}")
```

## Learn from Experience

```python
await agent.reflect_and_improve()
```
