"""
mcp/core/agent_registry.py — Agent registration and discovery.

Agents register by *role* (e.g. "explorer", "test_planner", "executor").
The orchestrator retrieves agents by role when executing pipeline stages.
"""

from __future__ import annotations

from typing import Any, Callable, Awaitable

from mcp.core.execution_context import ExecutionContext


# Type alias for an agent callable.
# Every agent is an async function:  (ExecutionContext, **kwargs) → dict[str, Any]
AgentCallable = Callable[..., Awaitable[dict[str, Any]]]


class AgentRegistry:
    """Singleton registry for pipeline agents."""

    def __init__(self) -> None:
        self._agents: dict[str, AgentCallable] = {}

    def register(self, role: str, agent_fn: AgentCallable) -> None:
        """Register an agent function under a role name."""
        self._agents[role.lower()] = agent_fn

    def get(self, role: str) -> AgentCallable:
        """Retrieve a registered agent by role."""
        key = role.lower()
        if key not in self._agents:
            available = ", ".join(sorted(self._agents)) or "(none)"
            raise KeyError(
                f"Agent role '{role}' is not registered. "
                f"Available agents: {available}"
            )
        return self._agents[key]

    def has(self, role: str) -> bool:
        return role.lower() in self._agents

    def list_roles(self) -> list[str]:
        """Return sorted list of registered agent roles."""
        return sorted(self._agents)

    def __repr__(self) -> str:
        return f"AgentRegistry(roles={self.list_roles()})"


# Global singleton.
agent_registry = AgentRegistry()
