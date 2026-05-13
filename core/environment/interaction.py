from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import hashlib
import json
import os
import random
import re
import subprocess
import tempfile
import uuid


class Capability(Enum):
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    LIST_DIRECTORY = "list_directory"
    EXECUTE_COMMAND = "execute_command"
    RUN_CODE = "run_code"


@dataclass
class PolicyRule:
    capability: Capability
    allowed: bool = True
    allowed_paths: List[str] = field(default_factory=list)
    denied_paths: List[str] = field(default_factory=list)
    allowed_commands: List[str] = field(default_factory=list)
    max_timeout_sec: int = 60


@dataclass
class ExecutionEvent:
    event_id: str
    session_id: str
    capability: str
    timestamp: str
    payload: Dict[str, Any]
    result: Dict[str, Any]


@dataclass
class ExecutionSession:
    session_id: str
    created_at: str
    deterministic_seed: int
    safe_mode: bool = False
    active: bool = True
    crash_detected: bool = False
    recovery_point: int = 0
    events: List[ExecutionEvent] = field(default_factory=list)


class EnvironmentInteraction:
    """Environment Layer Pro: policy, secret isolation, replay and recovery."""

    def __init__(self):
        self.file_operations_count = 0
        self.code_executions_count = 0
        self.os_interactions_count = 0
        self.environment_feedback: List[Dict[str, Any]] = []

        self.base_dir = os.getcwd()
        self.secrets_map: Dict[str, str] = {}
        self.policy_rules: Dict[Capability, PolicyRule] = {
            Capability.READ_FILE: PolicyRule(
                capability=Capability.READ_FILE,
                allowed=True,
                allowed_paths=[self.base_dir],
            ),
            Capability.WRITE_FILE: PolicyRule(
                capability=Capability.WRITE_FILE,
                allowed=True,
                allowed_paths=[self.base_dir],
                denied_paths=[os.path.join(self.base_dir, ".git")],
            ),
            Capability.LIST_DIRECTORY: PolicyRule(
                capability=Capability.LIST_DIRECTORY,
                allowed=True,
                allowed_paths=[self.base_dir],
            ),
            Capability.EXECUTE_COMMAND: PolicyRule(
                capability=Capability.EXECUTE_COMMAND,
                allowed=True,
                allowed_commands=["python", "pytest", "git", "echo", "dir", "ls"],
                max_timeout_sec=90,
            ),
            Capability.RUN_CODE: PolicyRule(
                capability=Capability.RUN_CODE,
                allowed=True,
                max_timeout_sec=45,
            ),
        }

        self.sessions: Dict[str, ExecutionSession] = {}
        self.active_session_id: Optional[str] = None

    async def start_session(self, deterministic_seed: Optional[int] = None, safe_mode: bool = False) -> Dict[str, Any]:
        seed = deterministic_seed if deterministic_seed is not None else random.randint(1, 1_000_000)
        random.seed(seed)
        session = ExecutionSession(
            session_id=str(uuid.uuid4()),
            created_at=datetime.now().isoformat(),
            deterministic_seed=seed,
            safe_mode=safe_mode,
        )
        self.sessions[session.session_id] = session
        self.active_session_id = session.session_id
        return {"session_id": session.session_id, "deterministic_seed": seed, "safe_mode": safe_mode}

    async def end_session(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        sid = session_id or self.active_session_id
        if not sid or sid not in self.sessions:
            return {"success": False, "error": "session_not_found"}
        self.sessions[sid].active = False
        if self.active_session_id == sid:
            self.active_session_id = None
        return {"success": True, "session_id": sid, "events": len(self.sessions[sid].events)}

    async def configure_policy(
        self,
        capability: str,
        allowed: bool,
        allowed_paths: Optional[List[str]] = None,
        denied_paths: Optional[List[str]] = None,
        allowed_commands: Optional[List[str]] = None,
        max_timeout_sec: Optional[int] = None,
    ) -> Dict[str, Any]:
        cap = Capability(capability)
        rule = self.policy_rules[cap]
        rule.allowed = allowed
        if allowed_paths is not None:
            rule.allowed_paths = [os.path.abspath(p) for p in allowed_paths]
        if denied_paths is not None:
            rule.denied_paths = [os.path.abspath(p) for p in denied_paths]
        if allowed_commands is not None:
            rule.allowed_commands = allowed_commands
        if max_timeout_sec is not None:
            rule.max_timeout_sec = max(1, int(max_timeout_sec))
        return {"success": True, "policy": self._rule_to_dict(rule)}

    async def isolate_secret(self, key: str, value: str) -> Dict[str, Any]:
        self.secrets_map[key] = value
        return {"success": True, "key": key, "masked": self._mask_secret(value)}

    async def read_file(self, path: str) -> Dict[str, Any]:
        allowed, reason = self._authorize(Capability.READ_FILE, path=path)
        if not allowed:
            return self._deny(reason)
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            content = self._redact_secrets(content)
            self.file_operations_count += 1
            result = {
                "success": True,
                "content": content,
                "size": len(content),
                "timestamp": datetime.now().isoformat(),
            }
            await self._log_event(Capability.READ_FILE, {"path": path}, result)
            return result
        except Exception as e:
            result = {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}
            await self._log_event(Capability.READ_FILE, {"path": path}, result)
            return result

    async def write_file(self, path: str, content: str) -> Dict[str, Any]:
        allowed, reason = self._authorize(Capability.WRITE_FILE, path=path)
        if not allowed:
            return self._deny(reason)
        try:
            content = self._redact_secrets(content)
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self.file_operations_count += 1
            result = {
                "success": True,
                "path": path,
                "size": len(content),
                "timestamp": datetime.now().isoformat(),
            }
            await self._log_event(Capability.WRITE_FILE, {"path": path, "size": len(content)}, result)
            return result
        except Exception as e:
            result = {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}
            await self._log_event(Capability.WRITE_FILE, {"path": path}, result)
            return result

    async def execute_system_command(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        allowed, reason = self._authorize(Capability.EXECUTE_COMMAND, command=command)
        if not allowed:
            return self._deny(reason)

        rule = self.policy_rules[Capability.EXECUTE_COMMAND]
        eff_timeout = min(timeout, rule.max_timeout_sec)
        try:
            normalized = self._replace_secret_refs(command)
            result_proc = subprocess.run(
                normalized,
                shell=True,
                capture_output=True,
                timeout=eff_timeout,
                text=True,
            )
            self.os_interactions_count += 1
            result = {
                "success": result_proc.returncode == 0,
                "stdout": self._redact_secrets(result_proc.stdout[:2000]),
                "stderr": self._redact_secrets(result_proc.stderr[:2000]),
                "returncode": result_proc.returncode,
                "timestamp": datetime.now().isoformat(),
            }
            self.environment_feedback.append(result)
            await self._log_event(Capability.EXECUTE_COMMAND, {"command": command, "timeout": eff_timeout}, result)
            return result
        except subprocess.TimeoutExpired:
            result = {"success": False, "error": "Command timeout", "timestamp": datetime.now().isoformat()}
            await self._log_event(Capability.EXECUTE_COMMAND, {"command": command, "timeout": eff_timeout}, result)
            return result
        except Exception as e:
            result = {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}
            await self._log_event(Capability.EXECUTE_COMMAND, {"command": command, "timeout": eff_timeout}, result)
            return result

    async def list_directory(self, path: str) -> Dict[str, Any]:
        allowed, reason = self._authorize(Capability.LIST_DIRECTORY, path=path)
        if not allowed:
            return self._deny(reason)
        try:
            files = []
            for item in os.listdir(path):
                full = os.path.join(path, item)
                files.append(
                    {
                        "name": item,
                        "is_dir": os.path.isdir(full),
                        "size": os.path.getsize(full) if os.path.isfile(full) else None,
                    }
                )
            self.file_operations_count += 1
            result = {"success": True, "path": path, "files": files, "count": len(files), "timestamp": datetime.now().isoformat()}
            await self._log_event(Capability.LIST_DIRECTORY, {"path": path}, result)
            return result
        except Exception as e:
            result = {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}
            await self._log_event(Capability.LIST_DIRECTORY, {"path": path}, result)
            return result

    async def run_code_in_environment(self, code: str, language: str = "python") -> Dict[str, Any]:
        allowed, reason = self._authorize(Capability.RUN_CODE)
        if not allowed:
            return self._deny(reason)

        try:
            stable_code = self._normalize_code_for_determinism(code)
            with tempfile.NamedTemporaryFile(mode="w", suffix=f".{language}", delete=False) as f:
                f.write(stable_code)
                temp_file = f.name

            if language == "python":
                cmd = f"python {temp_file}"
            else:
                cmd = f"{language} {temp_file}"

            result = await self.execute_system_command(cmd, timeout=self.policy_rules[Capability.RUN_CODE].max_timeout_sec)
            self.code_executions_count += 1

            try:
                os.unlink(temp_file)
            except Exception:
                pass
            await self._log_event(Capability.RUN_CODE, {"language": language, "hash": self._hash_text(stable_code)}, result)
            return result
        except Exception as e:
            result = {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}
            await self._log_event(Capability.RUN_CODE, {"language": language}, result)
            return result

    async def replay_session(self, session_id: str, deterministic: bool = True) -> Dict[str, Any]:
        session = self.sessions.get(session_id)
        if not session:
            return {"success": False, "error": "session_not_found"}

        replayed = []
        if deterministic:
            random.seed(session.deterministic_seed)

        for event in session.events:
            replayed.append(
                {
                    "event_id": event.event_id,
                    "capability": event.capability,
                    "payload_hash": self._hash_text(json.dumps(event.payload, sort_keys=True)),
                    "result_hash": self._hash_text(json.dumps(event.result, sort_keys=True)),
                }
            )

        return {
            "success": True,
            "session_id": session_id,
            "deterministic": deterministic,
            "events_replayed": len(replayed),
            "replay_trace": replayed,
        }

    async def recover_session(self, session_id: str, from_event_index: Optional[int] = None) -> Dict[str, Any]:
        session = self.sessions.get(session_id)
        if not session:
            return {"success": False, "error": "session_not_found"}

        idx = from_event_index if from_event_index is not None else session.recovery_point
        idx = max(0, min(idx, len(session.events)))
        session.crash_detected = False
        session.active = True
        session.recovery_point = idx

        return {
            "success": True,
            "session_id": session_id,
            "recovered_from_event": idx,
            "remaining_events": len(session.events) - idx,
            "deterministic_seed": session.deterministic_seed,
        }

    async def mark_crash(self, session_id: Optional[str], reason: str) -> Dict[str, Any]:
        sid = session_id or self.active_session_id
        if not sid or sid not in self.sessions:
            return {"success": False, "error": "session_not_found"}
        session = self.sessions[sid]
        session.crash_detected = True
        session.active = False
        session.recovery_point = len(session.events)
        return {"success": True, "session_id": sid, "reason": reason, "recovery_point": session.recovery_point}

    async def get_environment_stats(self) -> Dict[str, Any]:
        return {
            "file_operations": self.file_operations_count,
            "code_executions": self.code_executions_count,
            "os_interactions": self.os_interactions_count,
            "total_interactions": self.file_operations_count + self.code_executions_count + self.os_interactions_count,
            "recent_feedback": self.environment_feedback[-10:],
            "active_session_id": self.active_session_id,
            "sessions_total": len(self.sessions),
            "policy": {cap.value: self._rule_to_dict(rule) for cap, rule in self.policy_rules.items()},
        }

    def _authorize(self, capability: Capability, path: Optional[str] = None, command: Optional[str] = None) -> tuple[bool, str]:
        rule = self.policy_rules[capability]
        if not rule.allowed:
            return False, f"capability_disabled:{capability.value}"

        if path:
            abs_path = os.path.abspath(path)
            if rule.allowed_paths and not any(abs_path.startswith(p) for p in rule.allowed_paths):
                return False, "path_not_allowed"
            if any(abs_path.startswith(p) for p in rule.denied_paths):
                return False, "path_denied"

        if command and rule.allowed_commands:
            cmd_name = command.strip().split(" ")[0].lower()
            if cmd_name not in [c.lower() for c in rule.allowed_commands]:
                return False, "command_not_allowed"

        if self.active_session_id:
            sess = self.sessions[self.active_session_id]
            if sess.safe_mode and capability in (Capability.EXECUTE_COMMAND, Capability.RUN_CODE):
                return False, "blocked_by_safe_mode"

        return True, "ok"

    async def _log_event(self, capability: Capability, payload: Dict[str, Any], result: Dict[str, Any]) -> None:
        sid = self.active_session_id
        if not sid:
            return
        session = self.sessions.get(sid)
        if not session or not session.active:
            return
        event = ExecutionEvent(
            event_id=str(uuid.uuid4()),
            session_id=sid,
            capability=capability.value,
            timestamp=datetime.now().isoformat(),
            payload=payload,
            result=result,
        )
        session.events.append(event)

    def _replace_secret_refs(self, text: str) -> str:
        pattern = re.compile(r"\{\{secret:([A-Za-z0-9_\-]+)\}\}")

        def repl(match):
            key = match.group(1)
            return self.secrets_map.get(key, "")

        return pattern.sub(repl, text)

    def _redact_secrets(self, text: str) -> str:
        if not text:
            return text
        redacted = text
        for _, value in self.secrets_map.items():
            if value:
                redacted = redacted.replace(value, "***REDACTED***")
        return redacted

    def _normalize_code_for_determinism(self, code: str) -> str:
        stable_lines = [line.rstrip() for line in code.splitlines()]
        return "\n".join(stable_lines).strip() + "\n"

    def _mask_secret(self, value: str) -> str:
        if len(value) <= 4:
            return "*" * len(value)
        return value[:2] + "*" * (len(value) - 4) + value[-2:]

    def _hash_text(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:16]

    def _rule_to_dict(self, rule: PolicyRule) -> Dict[str, Any]:
        return {
            "capability": rule.capability.value,
            "allowed": rule.allowed,
            "allowed_paths": rule.allowed_paths,
            "denied_paths": rule.denied_paths,
            "allowed_commands": rule.allowed_commands,
            "max_timeout_sec": rule.max_timeout_sec,
        }

    def _deny(self, reason: str) -> Dict[str, Any]:
        return {"success": False, "error": f"policy_denied:{reason}", "timestamp": datetime.now().isoformat()}
