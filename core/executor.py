import asyncio
import subprocess
import tempfile
import os
import sys
from typing import Dict, Any, Tuple


class CodeExecutor:
    def __init__(self, timeout: int = 30, max_memory_mb: int = 512, temp_dir: str = ".tmp_exec"):
        self.timeout = timeout
        self.max_memory_mb = max_memory_mb
        self.temp_dir = os.path.abspath(temp_dir)
        os.makedirs(self.temp_dir, exist_ok=True)

    async def execute(self, code: str, language: str = "python") -> Dict[str, Any]:
        try:
            if language == "python":
                return await self._execute_python(code)
            elif language == "javascript":
                return await self._execute_javascript(code)
            else:
                return {
                    "error": f"Unsupported language: {language}",
                    "output": "",
                    "returncode": 1,
                }
        except asyncio.TimeoutError:
            return {
                "error": f"Execution timeout ({self.timeout}s)",
                "output": "",
                "returncode": 124,
            }
        except Exception as e:
            return {
                "error": str(e),
                "output": "",
                "returncode": 1,
            }

    async def _execute_python(self, code: str) -> Dict[str, Any]:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, dir=self.temp_dir) as f:
            f.write(code)
            temp_file = f.name

        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                temp_file,
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
                raise

            output = stdout.decode("utf-8", errors="ignore")
            error = stderr.decode("utf-8", errors="ignore")

            return {
                "error": error if error else None,
                "output": output,
                "returncode": process.returncode,
            }
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    async def _execute_javascript(self, code: str) -> Dict[str, Any]:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False, dir=self.temp_dir) as f:
            f.write(code)
            temp_file = f.name

        try:
            process = await asyncio.create_subprocess_exec(
                "node",
                temp_file,
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
                raise

            output = stdout.decode("utf-8", errors="ignore")
            error = stderr.decode("utf-8", errors="ignore")

            return {
                "error": error if error else None,
                "output": output,
                "returncode": process.returncode,
            }
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
