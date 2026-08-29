"""
mcp/modules/audit/module.py — Audit business module implementation.
"""

from __future__ import annotations

from typing import Any, Callable, Awaitable
from mcp.modules.base_module import BaseModule
from mcp.modules.audit.docs import get_expected_behaviors
from mcp.modules.audit.workflows import (
    navigate_to_audit,
    create_quick_audit_workflow,
    import_stock_sheet_workflow,
    verify_counting_and_tracker_workflow,
)


class AuditModule(BaseModule):
    """Audit Business Module implementation for MCP QA Platform."""

    @property
    def name(self) -> str:
        return "audit"

    @property
    def display_name(self) -> str:
        return "Audit Management"

    @property
    def default_route(self) -> str:
        return "/home/audit"

    def get_workflows(self) -> dict[str, list[Any]]:
        return {
            "navigate_to_audit": [navigate_to_audit],
            "create_quick_audit": [navigate_to_audit, create_quick_audit_workflow],
            "import_stock_sheet": [navigate_to_audit, create_quick_audit_workflow, import_stock_sheet_workflow],
            "verify_audit_tracker": [
                navigate_to_audit,
                create_quick_audit_workflow,
                import_stock_sheet_workflow,
                verify_counting_and_tracker_workflow,
            ],
        }

    def get_expected_behaviors(self) -> dict[str, Any]:
        return get_expected_behaviors()
