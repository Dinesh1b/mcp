"""
mcp/modules/finance/module.py — Finance business module implementation.
"""

from __future__ import annotations

from typing import Any
from mcp.modules.base_module import BaseModule
from mcp.modules.finance.docs import get_expected_behaviors
from mcp.modules.finance.workflows import (
    navigate_to_finance,
    purchase_form_validation_workflow,
)


class FinanceModule(BaseModule):
    """Finance & Purchase Business Module implementation for MCP QA Platform."""

    @property
    def name(self) -> str:
        return "finance"

    @property
    def display_name(self) -> str:
        return "Finance & Purchases"

    @property
    def default_route(self) -> str:
        return "/home/purchase/newpurchase"

    def get_workflows(self) -> dict[str, list[Any]]:
        return {
            "navigate_to_finance": [navigate_to_finance],
            "purchase_validation": [navigate_to_finance, purchase_form_validation_workflow],
        }

    def get_expected_behaviors(self) -> dict[str, Any]:
        return get_expected_behaviors()
