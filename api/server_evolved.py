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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
