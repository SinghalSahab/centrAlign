import asyncio
import hashlib
import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional

from app.agent.browser import HTTPBrowser
from app.agent.errors import ErrorClassifier
from app.agent.llm import GeminiLLMClient
from app.agent.memory import MemoryManager
from app.agent.permissions import PermissionManager
from app.agent.prompts import build_system_prompt
from app.agent.tools import ToolExecutor
from app.db import execute, fetch_one, execute_returning_id

logger = logging.getLogger("agent.loop")

class AgentLoop:
    """Generic Autonomous Agent Runtime (~200 lines, zero hardcoded role logic)."""

    def __init__(
        self,
        run_id: str,
        role_id: str,
        task: str,
        auto_approve: bool = True,
        faults: Optional[List[str]] = None,
        base_url: str = "http://localhost:8000",
        app_instance: Optional[Any] = None,
        messenger: Optional[Any] = None,
        step_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        self.run_id = run_id
        self.role_id = role_id.lower()
        self.task = task
        self.auto_approve = auto_approve
        self.faults = faults or []
        self.step_callback = step_callback

        # System Components
        self.permission_mgr = PermissionManager(self.role_id)
        self.memory = MemoryManager(self.run_id)
        self.browser = HTTPBrowser(base_url=base_url, run_id=self.run_id, app_instance=app_instance)
        self.llm = GeminiLLMClient()
        self.tools = ToolExecutor(self.run_id, self.browser, self.memory, messenger=messenger)
        self.system_prompt = build_system_prompt(self.permission_mgr.config)

        # Loop guards & metrics
        self.max_steps = 40
        self.max_wall_time = 300 # 5 minutes
        self.history: List[Dict[str, Any]] = []
        self.action_fingerprints: List[str] = []
        self.loop_warning_issued = False

    def _hash_action(self, tool_name: str, args: Dict[str, Any], page_url: str) -> str:
        s = f"{tool_name}:{json.dumps(args, sort_keys=True)}:{page_url}"
        return hashlib.md5(s.encode()).hexdigest()

    async def run(self) -> Dict[str, Any]:
        """Execute the agent loop until finish is called or limit exceeded."""
        logger.info(f"Starting agent run {self.run_id} for role '{self.role_id}'")
        start_time = time.time()
        step_number = 0

        # Initial prompt in history
        self.history.append({"role": "user", "content": f"Task: {self.task}"})

        # Ensure run record exists
        await execute(
            """INSERT INTO runs (id, role, task, status, faults, auto_approve)
               VALUES (%s, %s, %s, 'running', %s, %s)
               ON CONFLICT (id) DO UPDATE SET status = 'running'""",
            (self.run_id, self.role_id, self.task, self.faults, self.auto_approve)
        )

        try:
            while step_number < self.max_steps:
                step_number += 1

                # Check wall time
                if time.time() - start_time > self.max_wall_time:
                    logger.warning("Max wall time exceeded.")
                    break

                # Inject current memory context if facts exist
                memory_ctx = await self.memory.format_memory_context()
                augmented_prompt = f"{self.system_prompt}\n\n{memory_ctx}"

                # Generate next step from LLM
                thought, tool_call, error = await self.llm.generate_step(
                    system_instruction=augmented_prompt,
                    history=self.history,
                    allowed_tools=self.permission_mgr.allowed_tools
                )

                if error:
                    category, recovery = ErrorClassifier.classify(error)
                    await self._record_step(step_number, "error", None, None, None, error, category, recovery)
                    self.history.append({"role": "user", "content": f"[SYSTEM ERROR]: {error}. Recovery suggestion: {recovery}"})
                    continue

                if not tool_call:
                    # Model gave a response without tool call
                    await self._record_step(step_number, "thought", None, None, None, thought, None, None)
                    self.history.append({"role": "model", "content": thought})
                    continue

                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                logger.info(f"Step {step_number}: {tool_name} with {tool_args}")

                # 1. Permission check
                denial = await self.permission_mgr.check_permission(self.run_id, tool_name, tool_args)
                if denial:
                    category, recovery = ErrorClassifier.classify(denial["message"])
                    await self._record_step(
                        step_number, "denial", tool_name, tool_args, denial,
                        denial["message"], category, recovery
                    )
                    self.history.append({"role": "user", "content": f"[PERMISSION DENIED]: {denial['message']}. Please report this constraint or adapt."})
                    continue

                # 2. Loop Detection (same tool + args + page hash 3 times)
                current_url = self.browser.current_url
                fp = self._hash_action(tool_name, tool_args, current_url)
                self.action_fingerprints.append(fp)
                if self.action_fingerprints.count(fp) >= 3 and not self.loop_warning_issued:
                    self.loop_warning_issued = True
                    warning_msg = (
                        "Warning: Loop detected. You have performed the identical action 3 times without state progress. "
                        "You MUST change strategy immediately or escalate via ask_user."
                    )
                    self.history.append({"role": "user", "content": warning_msg})

                # 3. Human Approval Gate
                is_write = tool_name in ["web_submit", "message_candidate"]
                if is_write and not self.auto_approve:
                    # Record pending approval and pause
                    await execute(
                        "INSERT INTO approvals (run_id, tool_name, tool_args, reason) VALUES (%s, %s, %s, %s)",
                        (self.run_id, tool_name, tool_args, f"Agent requested to execute write tool {tool_name}")
                    )
                    await execute("UPDATE runs SET status = 'waiting_approval' WHERE id = %s", (self.run_id,))
                    logger.info("Paused run waiting for human approval.")
                    return {"status": "waiting_approval", "tool_name": tool_name, "tool_args": tool_args}

                # 4. Execute tool
                tool_result = await self.tools.execute_tool(tool_name, tool_args)

                # Check if finish was called
                if tool_name == "finish" and isinstance(tool_result, dict) and tool_result.get("finished"):
                    summary = tool_result.get("summary", "")
                    claims = tool_result.get("claims", [])
                    final_status = tool_result.get("status", "completed")

                    await self._record_step(step_number, "finish", tool_name, tool_args, tool_result, summary, None, None)
                    await execute(
                        """UPDATE runs 
                           SET status = %s, summary = %s, claims = %s, completed_at = CURRENT_TIMESTAMP 
                           WHERE id = %s""",
                        (final_status, summary, claims, self.run_id)
                    )
                    logger.info(f"Run {self.run_id} completed successfully in {step_number} steps.")
                    return {
                        "run_id": self.run_id,
                        "status": final_status,
                        "summary": summary,
                        "claims": claims,
                        "steps_count": step_number
                    }

                # Check for errors in tool output
                error_category, recovery_action = None, None
                result_str = str(tool_result)
                if "error" in result_str.lower() or "conflict" in result_str.lower() or "alert" in result_str.lower():
                    error_category, recovery_action = ErrorClassifier.classify(result_str)

                # 5. Record step
                await self._record_step(
                    step_number, "action", tool_name, tool_args, tool_result,
                    result_str[:1000], error_category, recovery_action
                )

                # 6. Append to history for next iteration
                self.history.append({
                    "role": "model",
                    "content": thought,
                    "tool_call": {"name": tool_name, "args": tool_args}
                })
                self.history.append({
                    "role": "tool",
                    "content": tool_result
                })

            # Exceeded steps
            fail_summary = f"Exceeded maximum steps cap ({self.max_steps})."
            await execute("UPDATE runs SET status = 'failed', error = %s WHERE id = %s", (fail_summary, self.run_id))
            return {"run_id": self.run_id, "status": "failed", "error": fail_summary, "steps_count": step_number}

        finally:
            await self.browser.close()

    async def _record_step(
        self,
        step_number: int,
        action_type: str,
        tool_name: Optional[str],
        tool_args: Optional[Dict[str, Any]],
        tool_result: Optional[Any],
        observation: Optional[str],
        error: Optional[str],
        recovery_action: Optional[str]
    ):
        step_data = {
            "run_id": self.run_id,
            "step_number": step_number,
            "action_type": action_type,
            "tool_name": tool_name,
            "tool_args": tool_args,
            "tool_result": tool_result if isinstance(tool_result, dict) else {"output": str(tool_result)},
            "observation": observation,
            "error": error,
            "recovery_action": recovery_action
        }

        await execute(
            """INSERT INTO steps (run_id, step_number, action_type, tool_name, tool_args, tool_result, observation, error, recovery_action)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                self.run_id, step_number, action_type, tool_name,
                tool_args, step_data["tool_result"], observation, error, recovery_action
            )
        )

        if self.step_callback:
            try:
                self.step_callback(step_data)
            except Exception as e:
                logger.warning(f"Error in step callback: {e}")
