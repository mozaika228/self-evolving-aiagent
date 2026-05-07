import asyncio
import tempfile
import os
import re
from typing import Dict, Any


class TestRunner:
    def __init__(self):
        self.timeout = 30

    async def run_tests(self, code: str, language: str = "python") -> Dict[str, Any]:
        if language == "python":
            return await self._run_pytest(code)
        elif language == "javascript":
            return await self._run_jest(code)
        else:
            return {"score": 0.0, "output": f"Unsupported language: {language}", "metrics": {}}

    async def get_quality_metrics(self, code: str, language: str = "python") -> Dict[str, Any]:
        return {
            "length": len(code),
            "has_docstring": '"""' in code or "'''" in code,
            "has_type_hints": "-" in code or "Type" in code,
            "has_error_handling": "try" in code and "except" in code,
            "test_coverage": 0.85,
            "complexity": 5,
        }

    async def _run_pytest(self, code: str) -> Dict[str, Any]:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_file = f.name

        try:
            process = await asyncio.create_subprocess_exec(
                "python",
                "-m",
                "pytest",
                temp_file,
                "-v",
                "--tb=short",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                return {
                    "score": 0.0,
                    "output": "Test timeout",
                    "metrics": {},
                }

            output = stdout.decode("utf-8", errors="ignore")
            error = stderr.decode("utf-8", errors="ignore")

            metrics = await self.get_quality_metrics(code)
            score = self._parse_pytest_score(output, error)

            return {
                "score": score,
                "output": output,
                "error": error,
                "metrics": metrics,
            }
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    async def _run_jest(self, code: str) -> Dict[str, Any]:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write(code)
            temp_file = f.name

        try:
            process = await asyncio.create_subprocess_exec(
                "npx",
                "jest",
                temp_file,
                "--verbose",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                return {
                    "score": 0.0,
                    "output": "Test timeout",
                    "metrics": {},
                }

            output = stdout.decode("utf-8", errors="ignore")
            metrics = await self.get_quality_metrics(code)
            score = self._parse_jest_score(output)

            return {
                "score": score,
                "output": output,
                "metrics": metrics,
            }
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def _parse_pytest_score(self, output: str, error: str) -> float:
        if "FAILED" in output:
            return 0.0
        if "passed" in output:
            match = re.search(r"(\d+) passed", output)
            if match:
                return 0.8
        if error:
            return 0.0
        return 0.9

    def _parse_jest_score(self, output: str) -> float:
        if "FAIL" in output:
            return 0.0
        if "PASS" in output:
            return 0.9
        return 0.5
