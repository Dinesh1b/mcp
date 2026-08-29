"""
mcp/core/workflow_engine.py — Workflow sequence runner.

Executes a sequence of *workflow steps* for a given module.
A workflow step is an async callable that receives the PlaywrightClient
and ExecutionContext, performs actions, and returns a step result dict.
"""

from __future__ import annotations

import traceback
from typing import Any, Callable, Awaitable

from mcp.playwright_client import PlaywrightClient
from mcp.core.execution_context import ExecutionContext


# A workflow step: async (client, context) → dict
WorkflowStep = Callable[[PlaywrightClient, ExecutionContext], Awaitable[dict[str, Any]]]


class WorkflowEngine:
    """Runs a sequence of workflow steps, tracking progress and handling errors."""

    def __init__(self, context: ExecutionContext) -> None:
        self.context = context
        self.results: list[dict[str, Any]] = []

    async def run_workflow(
        self,
        name: str,
        steps: list[WorkflowStep],
        client: PlaywrightClient,
        *,
        stop_on_failure: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Execute workflow steps sequentially.

        Args:
            name: Human-readable workflow name for logging.
            steps: Ordered list of async step functions.
            client: Active PlaywrightClient session.
            stop_on_failure: If True, abort remaining steps on first failure.

        Returns:
            List of step result dicts.
        """
        workflow_results: list[dict[str, Any]] = []

        for i, step_fn in enumerate(steps, 1):
            step_name = getattr(step_fn, "__name__", f"step_{i}")
            result: dict[str, Any] = {
                "workflow": name,
                "step": step_name,
                "step_index": i,
                "status": "PASS",
                "data": {},
                "error": None,
            }

            try:
                step_data = await step_fn(client, self.context)
                result["data"] = step_data or {}
                result["status"] = step_data.get("status", "PASS") if step_data else "PASS"
            except Exception as exc:
                result["status"] = "BLOCKED"
                result["error"] = f"{type(exc).__name__}: {exc}"
                result["traceback"] = traceback.format_exc()

                if stop_on_failure:
                    workflow_results.append(result)
                    break

            workflow_results.append(result)

        self.results.extend(workflow_results)
        return workflow_results

    async def run_workflows(
        self,
        workflows: dict[str, list[WorkflowStep]],
        client: PlaywrightClient,
        *,
        stop_on_failure: bool = False,
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Run multiple named workflows sequentially.

        Args:
            workflows: Mapping of workflow_name → list of steps.
            client: Active PlaywrightClient session.
            stop_on_failure: Per-workflow stop behavior.

        Returns:
            Mapping of workflow_name → list of step results.
        """
        all_results: dict[str, list[dict[str, Any]]] = {}
        for wf_name, steps in workflows.items():
            wf_results = await self.run_workflow(
                wf_name, steps, client, stop_on_failure=stop_on_failure
            )
            all_results[wf_name] = wf_results
        return all_results
