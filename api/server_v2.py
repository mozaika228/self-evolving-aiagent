from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.super_agent import SuperAgent
from core.agent import EvolvingAgent
from core.llm_engine import LLMEngine


app = FastAPI(title="Super-Evolving Agent", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

super_agent = SuperAgent()
agent = EvolvingAgent()
llm = LLMEngine()


class ExecuteRequest(BaseModel):
    task: str
    language: str = "python"
    learn: bool = True


class GeneticRequest(BaseModel):
    code: str
    generations: int = 10


class SelfModifyRequest(BaseModel):
    code: str
    tests: str
    description: str


@app.get("/health")
async def health():
    llm_health = await llm.check_health()
    return {
        "status": "healthy" if llm_health else "degraded",
        "version": "super-evolving",
    }


@app.post("/api/execute/evolution")
async def execute_with_evolution(request: ExecuteRequest):
    try:
        result = await super_agent.execute_with_evolution(
            task=request.task,
            language=request.language,
        )
        return {"status": "success", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/genetic/optimize")
async def genetic_optimize(request: GeneticRequest):
    try:
        result = await super_agent.genetic_optimization(
            initial_code=request.code,
            generations=request.generations,
        )
        return {"status": "success", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/self-modify")
async def self_modify(request: SelfModifyRequest):
    try:
        result = await super_agent.self_modify(
            code=request.code,
            tests=request.tests,
            description=request.description,
        )
        return {"status": "success", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/skills")
async def get_skills():
    try:
        stats = await super_agent.skill_system.get_statistics()
        return {"status": "success", **stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status")
async def get_status():
    try:
        status = await super_agent.get_status()
        return {"status": "success", **status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/execute")
async def execute_task(request: ExecuteRequest):
    try:
        result = await agent.execute(
            task=request.task,
            language=request.language,
            learn=request.learn,
        )
        return {
            "status": "success",
            "code": result.code,
            "test_score": result.test_score,
            "quality_metrics": result.quality_metrics,
            "iterations": result.iterations,
            "total_time": result.total_time,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
