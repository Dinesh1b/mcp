"""
mcp/modules/inventory/module.py — Inventory business module implementation.
"""

from __future__ import annotations

from typing import Any
from mcp.modules.base_module import BaseModule
from mcp.modules.inventory.docs import get_expected_behaviors
from mcp.modules.inventory.workflows import (
    navigate_to_inventory,
    search_and_filter_workflow,
    verify_item_groups_workflow,
)


class InventoryModule(BaseModule):
    """Inventory Business Module implementation for MCP QA Platform."""

    @property
    def name(self) -> str:
        return "inventory"

    @property
    def display_name(self) -> str:
        return "Inventory & Stock Management"

    @property
    def default_route(self) -> str:
        return "/home/purchase/newpurchase"

    def get_workflows(self) -> dict[str, list[Any]]:
        return {
            "navigate_to_inventory": [navigate_to_inventory],
            "search_and_filter": [navigate_to_inventory, search_and_filter_workflow],
            "item_groups": [navigate_to_inventory, verify_item_groups_workflow],
        }

    def get_expected_behaviors(self) -> dict[str, Any]:
        return get_expected_behaviors()
