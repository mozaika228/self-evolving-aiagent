# Super-Evolving Agent - Evolution System

## New Features

### 1. Skill System
- Extract successful solutions as reusable skills
- Compose skills for complex tasks
- Track usage and success rates

```python
await agent.skill_system.extract_skill(
    task="Fix authentication bug",
    code=working_code,
    test_score=0.95,
)
```

### 2. Hierarchical Memory (4 Levels)
- L0: Raw logs
- L1: Insights
- L2: Knowledge
- L3: Skills  
- L4: Strategy

### 3. Evaluation System
- Success rate
- Latency efficiency
- Code quality
- Documentation
- Test coverage

### 4. Evolution Loop
- Iterative improvement with rollback
- Automatic code enhancement
- Pattern extraction

### 5. Self-Modification Runtime
- Safe code generation & testing
- Automatic PR creation
- Rollback on failure

### 6. Multi-Agent Architecture
- Planner → plans task
- Executor → executes plan
- Critic → evaluates results
- Evolver → suggests improvements

### 7. Genetic Algorithm
- Population-based optimization
- Mutations and crossover
- Fitness-based selection
- Generation tracking

## API Endpoints

### Evolution Execution
```bash
curl -X POST "http://localhost:8000/api/execute/evolution" \
  -H "Content-Type: application/json" \
  -d '{"task": "Build REST API", "language": "python"}'
```

### Genetic Optimization
```bash
curl -X POST "http://localhost:8000/api/genetic/optimize" \
  -H "Content-Type: application/json" \
  -d '{"code": "def f(): pass", "generations": 10}'
```

### Self-Modification
```bash
curl -X POST "http://localhost:8000/api/self-modify" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def main(): pass",
    "tests": "def test_main(): pass",
    "description": "Improve main function"
  }'
```

### Get Skills
```bash
curl http://localhost:8000/api/skills
```

### System Status
```bash
curl http://localhost:8000/api/status
```

## Usage Example

```python
from core.super_agent import SuperAgent

agent = SuperAgent()

result = await agent.execute_with_evolution(
    "Implement quicksort with O(n log n) guarantee"
)

print(f"Best score: {result['score']:.1%}")
print(f"Skill extracted: {result['skill_extracted']}")
print(f"Time: {result['time_elapsed']:.2f}s")
```

## Architecture Comparison

| Feature | Original | Super |
|---------|----------|-------|
| Self-improving | ✓ | ✓ |
| Self-evolving | ✗ | ✓ |
| Skill extraction | ✗ | ✓ |
| Genetic optimization | ✗ | ✓ |
| Self-modification | ✗ | ✓ |
| Multi-agent | ✗ | ✓ |
| Hierarchical memory | ✗ | ✓ |
| Evaluation system | ✗ | ✓ |
