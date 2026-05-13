import pytest

httpx = pytest.importorskip("httpx")
if not hasattr(httpx, "BaseTransport"):
    pytest.skip("Incompatible httpx version for Starlette TestClient", allow_module_level=True)

from fastapi.testclient import TestClient

from api.server_evolved import app
import api.server_evolved as server


def test_control_plane_status_endpoint():
    client = TestClient(app)
    response = client.get("/api/control-plane/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "memory" in data
    assert "risks" in data


def test_run_evolution_cycle_endpoint(monkeypatch):
    async def fake_run_cycle(task: str, language: str = "python"):
        return {
            "cycle": {"task": task, "execution": {"score": 1.0}},
            "control_plane": {"risks": []},
        }

    monkeypatch.setattr(server.agent, "run_evolution_cycle", fake_run_cycle)

    client = TestClient(app)
    response = client.post(
        "/api/evolution/run-cycle",
        json={"task": "smoke", "language": "python"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["cycle"]["task"] == "smoke"


def test_weekly_report_endpoint(monkeypatch):
    async def fake_weekly_report():
        return {
            "period_days": 7,
            "summary": {"executions": 3, "success_rate": 1.0},
            "skill_diff": {"added_tools": ["tool_a"], "removed_tools": []},
            "generated_at": "2026-05-13T00:00:00",
        }

    monkeypatch.setattr(server.agent, "generate_weekly_evolution_report", fake_weekly_report)

    client = TestClient(app)
    response = client.get("/api/reports/weekly-evolution")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["period_days"] == 7
    assert "skill_diff" in data


def test_evaluation_run_contains_gate():
    client = TestClient(app)
    response = client.post("/api/evaluation/run", json={"candidate_name": "integration_test"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "gate" in data
    assert "pass" in data["gate"]
