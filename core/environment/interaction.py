from typing import Dict, Any, List, Callable
from datetime import datetime
import os
import subprocess
import tempfile


class EnvironmentInteraction:
    """Взаимодействие агента с окружением"""
    
    def __init__(self):
        self.file_operations_count = 0
        self.code_executions_count = 0
        self.os_interactions_count = 0
        self.environment_feedback = []

    async def read_file(self, path: str) -> Dict[str, Any]:
        """Прочитать файл из окружения"""
        try:
            with open(path, 'r') as f:
                content = f.read()
            
            self.file_operations_count += 1
            
            return {
                "success": True,
                "content": content,
                "size": len(content),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def write_file(self, path: str, content: str) -> Dict[str, Any]:
        """Записать файл в окружение"""
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as f:
                f.write(content)
            
            self.file_operations_count += 1
            
            return {
                "success": True,
                "path": path,
                "size": len(content),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def execute_system_command(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """Выполнить системную команду"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                timeout=timeout,
                text=True,
            )
            
            self.os_interactions_count += 1
            
            feedback = {
                "success": result.returncode == 0,
                "stdout": result.stdout[:1000],  # Первые 1000 символов
                "stderr": result.stderr[:1000],
                "returncode": result.returncode,
                "timestamp": datetime.now().isoformat(),
            }
            
            self.environment_feedback.append(feedback)
            return feedback
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Command timeout",
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def list_directory(self, path: str) -> Dict[str, Any]:
        """Список файлов в директории"""
        try:
            items = os.listdir(path)
            files = []
            
            for item in items:
                full_path = os.path.join(path, item)
                files.append({
                    "name": item,
                    "is_dir": os.path.isdir(full_path),
                    "size": os.path.getsize(full_path) if os.path.isfile(full_path) else None,
                })
            
            self.file_operations_count += 1
            
            return {
                "success": True,
                "path": path,
                "files": files,
                "count": len(files),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def run_code_in_environment(
        self,
        code: str,
        language: str = "python",
    ) -> Dict[str, Any]:
        """Запустить код в изолированной среде"""
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix=f'.{language}',
                delete=False,
            ) as f:
                f.write(code)
                temp_file = f.name
            
            result = await self.execute_system_command(f"{language} {temp_file}")
            
            self.code_executions_count += 1
            
            # Очистка
            try:
                os.unlink(temp_file)
            except:
                pass
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def get_environment_stats(self) -> Dict[str, Any]:
        """Статистика взаимодействия с окружением"""
        return {
            "file_operations": self.file_operations_count,
            "code_executions": self.code_executions_count,
            "os_interactions": self.os_interactions_count,
            "total_interactions": (
                self.file_operations_count +
                self.code_executions_count +
                self.os_interactions_count
            ),
            "recent_feedback": self.environment_feedback[-10:],
        }
