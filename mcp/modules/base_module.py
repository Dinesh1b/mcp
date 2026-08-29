"""
mcp/modules/base_module.py — Abstract base class for business modules.

Every business module (Audit, Inventory, Finance, and future extensions)
inherits from BaseModule and implements its interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Awaitable, TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.core.execution_context import ExecutionContext
    from mcp.playwright_client import PlaywrightClient

WorkflowStep = Callable[["PlaywrightClient", "ExecutionContext"], Awaitable[dict[str, Any]]]


class BaseModule(ABC):
    """
    Abstract base for any QA Business Module.
    Encapsulates module metadata, routes, workflows, documentation, and memory defaults.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Module identifier (e.g. 'audit', 'inventory', 'finance')."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name (e.g. 'Audit Management')."""
        pass

    @property
    @abstractmethod
    def default_route(self) -> str:
        """Default module URL route or hash (e.g. '/home/audit')."""
        pass

    @abstractmethod
    def get_workflows(self) -> dict[str, list[WorkflowStep]]:
        """
        Return a mapping of workflow_name -> list of async step callables.
        """
        pass

    @abstractmethod
    def get_expected_behaviors(self) -> dict[str, Any]:
        """
        Return documented expected behaviors for this module's features.
        """
        pass

    def get_initial_memory(self) -> dict[str, Any]:
        """
        Return initial knowledge snapshot for this module.
        Can be overridden with known selectors, navigation paths, etc.
        """
        return {
            "module": self.name,
            "display_name": self.display_name,
            "default_route": self.default_route,
            "known_workflows": list(self.get_workflows().keys()),
            "discovered_pages": [],
            "stable_selectors": {},
            "known_defects": [],
            "test_history": [],
        }
