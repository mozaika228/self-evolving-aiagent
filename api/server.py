from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import asyncio

from core.agent import EvolvingAgent
from core.llm_engine import LLMEngine


app = FastAPI(title="Self-Evolving Agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = EvolvingAgent()
llm = LLMEngine()


class ExecuteRequest(BaseModel):
    task: str
    language: str = "python"
    learn: bool = True


class ImproveRequest(BaseModel):
    code: str
    language: str = "python"


class SearchRequest(BaseModel):
    query: str
    limit: int = 5


class ReflectRequest(BaseModel):
    auto_update: bool = True


@app.get("/health")
async def health():
    llm_health = await llm.check_health()
    return {
        "status": "healthy" if llm_health else "degraded",
        "llm": "healthy" if llm_health else "unavailable",
    }


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
            "improvement": result.improvement,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/improve")
async def improve_code(request: ImproveRequest):
    try:
        improved = await agent.improve(
            code=request.code,
            language=request.language,
        )
        return {
            "status": "success",
            "original": request.code,
            "improved": improved,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/memory/search")
async def search_memory(request: SearchRequest):
    try:
        results = await agent.vector_store.search(
            query=request.query,
            limit=request.limit,
        )
        return {
            "status": "success",
            "query": request.query,
            "results": results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metrics")
async def get_metrics():
    try:
        stats = await agent.vector_store.get_statistics()
        policy_stats = await agent.rl_trainer.get_policy_stats()
        return {
            "status": "success",
            "memory": stats,
            "policy": policy_stats,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reflect")
async def reflect_and_improve(request: ReflectRequest):
    try:
        result = await agent.reflect_and_improve()
        return {
            "status": "success",
            **result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate")
async def generate_code(request: ExecuteRequest):
    try:
        code = await agent.generator.generate(
            task=request.task,
            language=request.language,
        )
        return {
            "status": "success",
            "code": code,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
