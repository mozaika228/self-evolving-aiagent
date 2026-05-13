# OPERATIONS

## Daily Cycle
1. Start API: `python -m uvicorn api.server_evolved:app --host 0.0.0.0 --port 8000 --reload`
2. Run one-click evolution cycle:
   - `POST /api/evolution/run-cycle`
   - Body: `{ "task": "...", "language": "python" }`
3. Check control plane:
   - `GET /api/control-plane/status`

## Risk Interpretation
- `safe_mode` risk: high priority. Pause autonomous tool synthesis and reduce command capabilities.
- `quality_trend` degrading: inspect critic backlog (`GET /api/critic/backlog`) and prioritize top items.
- `tool_degradation`: review disabled tools in `GET /api/evolution/registry`; retrain or re-approve only after benchmark recovery.
- `cold_memory`: run more successful cycles and nightly memory maintenance (`POST /api/memory/nightly`).

## Weekly Ops
1. Generate weekly report:
   - `GET /api/reports/weekly-evolution`
2. Review `skill_diff`:
   - `added_tools`: confirm value and monitor failures.
   - `removed_tools`: check for regression or over-strict disable threshold.

## Reference KPI Update
1. Run evaluation:
   - `POST /api/evaluation/run` with candidate name.
2. If regression gate is acceptable, update reference:
   - `POST /api/evaluation/reference`
3. CI enforces regression gate automatically via `tools/run_regression_gate.py`.

## Recovery
- Start deterministic session: `POST /api/environment/session/start`
- Replay: `POST /api/environment/replay`
- Recover from crash point: `POST /api/environment/recover`
