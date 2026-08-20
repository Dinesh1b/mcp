"""
workflows/exploratory_flows.py — Exploratory Flow Engine for Undocumented Modules.

Implements Phase 4.2:
Explores Sales, Purchases, and Reports without assuming rigid ERP pipelines (no assumed PO/PI/GRN or SO/SI/DN).
- Maps actual interactive actions directly from the live application
- Records observed behavior as candidate specs
- Reports findings strictly as OBSERVED / UNVERIFIABLE
"""

from __future__ import annotations

from typing import Any
from mcp.playwright_client import PlaywrightClient
from agent.memory_store import ModuleMemoryStore


async def explore_undocumented_module(
    client: PlaywrightClient,
    module_name: str,
) -> list[dict[str, Any]]:
    """
    Explores an undocumented module (Sales, Purchases, Reports), discovering
    actual buttons, forms, tables, and API responses.
    """
    memory = ModuleMemoryStore(module_name)
    findings: list[dict[str, Any]] = []

    norm_module = module_name.lower().strip()
    target_path = f"/{norm_module}"
    
    # Step 1: Navigate and map landing page
    step1: dict[str, Any] = {
        "step": 1,
        "name": f"Discover {module_name} Landing View",
        "doc_status": "UNDOCUMENTED",
        "action": f"Navigate to {target_path} and map available UI actions",
    }
    try:
        await client.navigate(f"{client.page.url.split('#')[0]}{target_path}")
        await client.wait_for_network_idle()
        screenshot = await client.screenshot(f"explore_{memory.module_key}_landing")

        # Discover interactive elements
        elements = await client.extract_interactive_elements()
        action_names = [el["text"] for el in elements if el.get("text") and len(el["text"]) < 25]

        # Check observed API requests
        net_logs = client.get_network_logs()
        api_endpoints = [n["url"] for n in net_logs if n.get("type") == "response"]

        step1["status"] = "OBSERVED"
        step1["actual"] = (
            f"Page mapped successfully. Found actions: [{', '.join(action_names[:8]) or 'None'}]. "
            f"Observed {len(api_endpoints)} network endpoints. No documented expected spec exists."
        )
        step1["evidence"] = {
            "screenshot": str(screenshot),
            "discovered_actions": action_names[:15],
            "api_endpoints": api_endpoints[:5],
        }

        # Store candidate spec in module memory
        memory.add_or_update_page({
            "url": await client.get_url(),
            "title": await client.get_title(),
            "discovered_actions": action_names,
            "doc_status": "UNDOCUMENTED",
        })

    except Exception as e:
        step1["status"] = "UNVERIFIABLE"
        step1["actual"] = f"Exploration could not complete: {e}"
        step1["evidence"] = {"error": str(e)}

    findings.append(step1)
    return findings
