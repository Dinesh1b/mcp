"""
agent/flow_engine.py — Business Flow Execution Engine.

Orchestrates Phase 4:
- Routes validated flows (Audit lifecycle, Inventory setup, Setup & Config) to full UI+API+Business validation.
- Routes undocumented flows (Sales, Purchases, Reports) to exploratory discovery.
"""

from __future__ import annotations

from typing import Any, Optional
from mcp.playwright_client import PlaywrightClient
from knowledge.rag_retriever import RAGRetriever
from workflows.audit_lifecycle import execute_audit_lifecycle
from workflows.inventory_setup import execute_inventory_setup
from workflows.setup_config import execute_setup_config_flow
from workflows.exploratory_flows import explore_undocumented_module


class FlowEngine:
    """Dispatches and coordinates business flows."""

    def __init__(self):
        self.retriever = RAGRetriever()

    async def execute_module_flow(
        self,
        client: PlaywrightClient,
        module_name: str,
        flow_type: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Execute the appropriate flow depending on doc coverage.
        """
        norm = module_name.lower().strip()

        # Validated Flows
        if "audit" in norm:
            return await execute_audit_lifecycle(client)
        elif "inventory" in norm or "item" in norm:
            return await execute_inventory_setup(client)
        elif "setup" in norm or "config" in norm or "user" in norm:
            return await execute_setup_config_flow(client)

        # Exploratory Flows (Sales, Purchases, Reports, or any undocumented area)
        return await explore_undocumented_module(client, module_name)
