# System Architecture

## Components

### Agent (core/agent.py)
Main orchestrator implementing self-reflection loop:
- Task execution
- Iterative improvement
- Learning from success
- Pattern extraction

### LLMEngine (core/llm_engine.py)
Ollama integration:
- Async code generation
- Streaming support
- Health checks
- Temperature/sampling control

### CodeGenerator (core/code_gen/generator.py)
Prompt engineering:
- Language-specific prompts
- Markdown extraction
- Code formatting
- Test generation

### CodeExecutor (core/executor.py)
Sandboxed execution:
- Process isolation
- Timeout handling
- Resource limits
- Error capture

### TestRunner (core/testing/test_runner.py)
Quality metrics:
- pytest integration
- Jest integration
- Code analysis
- Coverage calculation

### VectorStore (core/memory/vector_store.py)
Qdrant integration:
- Semantic search
- Solution storage
- Pattern recognition
- Statistics tracking

### RewardModel (core/rl/reward_model.py)
RL rewards calculation:
- Test score weight: 40%
- Code quality: 20%
- Efficiency: 20%
- Iterations penalty: 10%
- Innovation bonus: 10%

### RLTrainer (core/rl/trainer.py)
Policy learning:
- Experience replay buffer
- Policy versioning
- Batch updates
- Statistics tracking

## Self-Evolution Loop

```
┌──────────────────────┐
│   Task              │
└──────────┬──────────┘
           │
           ▼
┌────────────────────────────────────────────────────────────┐
│ Search similar solutions                                   │
│ in memory (vector DB)                                      │
└──────────┬─────────────────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────────────────┐
│ Generate code with LLM                                     │
│ (context-aware)                                            │
└──────────┬─────────────────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────────────────┐
│ Execute in sandbox                                         │
│ (secure, isolated)                                         │
└──────────┬─────────────────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────────────────┐
│ Run tests & metrics                                        │
│ (pytest, coverage)                                         │
└──────────┬─────────────────────────────────────────────────┘
           │
           ▼
       ┌──────────────────────────┐
       │ Score >= 0.95?           │
       └──┬──────────────────┬────┘
          │ NO        │ YES
          │           │
          │           ▼
          │      ┌─────────────────────────────────────────┐
          │      │ Save to memory                          │
          │      │ Calculate reward                        │
          │      └──────────┬────────────────────────────┘
          │                 │
          │                 ▼
          │           ┌─────────────────────────────────────────┐
          │           │ Update RL policy                        │
          │           └──────────┬──────────────────────────────┘
          │                      │
          │                      ▼
          │                 ┌─────────────────────────────────────────┐
          │                 │ Extract patterns                        │
          │                 └──────────┬──────────────────────────────┘
          │                            │
          └────────────────┬───────────┴──────────────────────────────┐
                           ▼                                           │
                      ┌──────────────────────────────┐                │
                      │  Continue?                   │                │
                      └──────────┬───────────────────┘                │
                                 │                                    ▼
                        Retry with                        Continue loop
                        analysis                          Reflect &
                                                          improve
```

## Data Flow

1. **Input**: Task description
2. **Memory Search**: Semantic search for similar solutions
3. **Code Gen**: LLM generates code with context
4. **Execution**: Safe sandbox execution
5. **Testing**: Comprehensive test suite
6. **Evaluation**: Quality metrics and score
7. **Learning**: Store solution, calculate reward, update policy
8. **Reflection**: Extract patterns, improve self

## Technology Stack

| Component | Tech |
|-----------|------|
| LLM | Ollama + DeepSeek Coder |
| Embeddings | sentence-transformers |
| Vector DB | Qdrant |
| RL Buffer | Redis |
| Execution | Docker/subprocess |
| Testing | pytest/Jest |
| API | FastAPI |
| Async | asyncio |

## Scalability

- **Horizontal**: Multiple agent instances
- **Vertical**: GPU acceleration for LLM
- **Memory**: Distributed Qdrant cluster
- **RL**: Distributed experience replay
