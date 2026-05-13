from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.evolved_agent import FullyEvolvedAgent
from core.llm_engine import LLMEngine


app = FastAPI(title="Fully-Evolved Agent", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = FullyEvolvedAgent()
llm = LLMEngine()


class ExecuteRequest(BaseModel):
    task: str
    language: str = "python"


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "fully-evolved"}


@app.post("/api/execute/evolved")
async def execute_evolved(request: ExecuteRequest):
    try:
        result = await agent.execute_with_full_evolution(
            task=request.task,
            language=request.language,
        )
        return {"status": "success", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status/full")
async def get_full_status():
    try:
        status = await agent.get_full_status()
        return {"status": "success", **status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/memory/nightly")
async def run_nightly_memory():
    try:
        result = await agent.run_nightly_memory_maintenance()
        return {"status": "success", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/critic/backlog")
async def get_critic_backlog(limit: int = 20):
    try:
        backlog = await agent.critic.get_improvement_backlog(limit=limit)
        return {"status": "success", "count": len(backlog), "items": backlog}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/evolution/registry")
async def get_evolution_registry():
    try:
        report = await agent.structural_evolution.get_registry_report()
        return {"status": "success", **report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ToolOutcomeRequest(BaseModel):
    tool_name: str
    success: bool
    score: float


@app.post("/api/evolution/tool-outcome")
async def update_tool_outcome(request: ToolOutcomeRequest):
    try:
        result = await agent.structural_evolution.update_tool_outcome(
            tool_name=request.tool_name,
            success=request.success,
            score=request.score,
        )
        return {"status": "success", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class StrategyPlanRequest(BaseModel):
    iterations: int = 5


class StrategyBudgetRequest(BaseModel):
    token_budget: int
    time_budget_sec: float


@app.post("/api/strategy/plan")
async def build_strategy_plan(request: StrategyPlanRequest):
    try:
        plan = await agent.strategy.build_iteration_plan(n_iterations=request.iterations)
        return {"status": "success", "iterations": request.iterations, "plan": plan}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/strategy/budget")
async def set_strategy_budget(request: StrategyBudgetRequest):
    try:
        result = await agent.strategy.set_budget(
            token_budget=request.token_budget,
            time_budget_sec=request.time_budget_sec,
        )
        return {"status": "success", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
