import asyncio
import tempfile
import os
import subprocess
from typing import Dict, Any
from datetime import datetime


class SelfModificationRuntime:
    def __init__(self, sandbox_dir: str = "/tmp/agent_sandbox"):
        self.sandbox_dir = sandbox_dir
        os.makedirs(sandbox_dir, exist_ok=True)

    async def create_and_test(
        self,
        code: str,
        tests: str,
        description: str,
    ) -> Dict[str, Any]:
        file_path = os.path.join(
            self.sandbox_dir,
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.py",
        )
        
        with open(file_path, "w") as f:
            f.write(code)
            f.write("\n\n")
            f.write(tests)
        
        result = await self._run_tests(file_path)
        
        return {
            "file_path": file_path,
            "success": result["returncode"] == 0,
            "output": result["output"],
            "error": result["error"],
        }

    async def create_pr(
        self,
        code: str,
        branch_name: str,
        message: str,
    ) -> Dict[str, Any]:
        file_path = os.path.join(self.sandbox_dir, f"{branch_name}.py")
        
        with open(file_path, "w") as f:
            f.write(code)
        
        return {
            "branch": branch_name,
            "file": file_path,
            "message": message,
            "status": "ready_for_review",
        }

    async def rollback_if_failed(
        self,
        code: str,
        previous_code: str,
    ) -> str:
        result = await self._validate_code(code)
        if not result["valid"]:
            return previous_code
        return code

    async def _run_tests(self, file_path: str) -> Dict[str, Any]:
        process = await asyncio.create_subprocess_exec(
            "python",
            "-m",
            "pytest",
            file_path,
            "-v",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)
        except asyncio.TimeoutError:
            process.kill()
            return {
                "returncode": 124,
                "output": "",
                "error": "Test timeout",
            }
        
        return {
            "returncode": process.returncode,
            "output": stdout.decode("utf-8", errors="ignore"),
            "error": stderr.decode("utf-8", errors="ignore"),
        }

    async def _validate_code(self, code: str) -> Dict[str, bool]:
        try:
            compile(code, "<string>", "exec")
            return {"valid": True}
        except SyntaxError:
            return {"valid": False}
