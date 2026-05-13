from __future__ import annotations

import json
import os
import sys
import importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

LAB_PATH = os.path.join(ROOT, "core", "evaluation", "lab.py")
spec = importlib.util.spec_from_file_location("evaluation_lab", LAB_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules["evaluation_lab"] = module
spec.loader.exec_module(module)

EvaluationLab = module.EvaluationLab
EvalResult = module.EvalResult


def main() -> int:
    lab = EvaluationLab()

    # Deterministic CI sample for stable gate behavior
    sample = [
        EvalResult("s1", True, 3.4, 1800, 0.82, 0.52, True, 1),
        EvalResult("s2", True, 3.6, 1900, 0.80, 0.49, True, 1),
        EvalResult("m1", True, 3.9, 2200, 0.78, 0.46, True, 2),
        EvalResult("m2", True, 4.0, 2300, 0.76, 0.45, True, 2),
        EvalResult("h1", True, 4.3, 2800, 0.74, 0.44, False, 2),
        EvalResult("h2", True, 4.4, 2900, 0.73, 0.43, False, 2),
    ]

    candidate_kpi = lab.evaluate_candidate(sample)
    reference_kpi = lab.load_reference()
    gate = lab.regression_gate(candidate_kpi, reference_kpi)

    report = {
        "candidate": "ci_candidate",
        "candidate_kpi": candidate_kpi,
        "reference_kpi": reference_kpi,
        "gate": gate,
    }
    print(json.dumps(report, indent=2))

    return 0 if gate["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
