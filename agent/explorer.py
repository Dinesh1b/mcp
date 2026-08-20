"""
agent/explorer.py — Application exploration using Playwright MCP with Doc-Coverage Reconciliation.

Implements Phase 2: Application Explorer.
Recursively maps:
Application -> Module -> Submodule -> Page -> Tab -> Section -> Elements/Actions

Cross-references discovered modules against documentation coverage:
- DOCUMENTED vs. UNDOCUMENTED tagging
- Records observed elements, selectors, and API endpoints into ModuleMemoryStore
- Detects discrepancies between reference docs and live app behavior
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from config.settings import settings
from mcp.playwright_client import PlaywrightClient
from knowledge.rag_retriever import RAGRetriever
from agent.memory_store import ModuleMemoryStore
from workflows.login import perform_login


async def explore_application(
    base_url: str | None = None,
    target_module: str | None = None,
) -> dict[str, Any]:
    """
    Explore the live application, reconcile against doc coverage,
    and update persistent module memory stores.

    Returns:
        Structured exploration data dictionary.
    """
    url = base_url or settings.base_url
    retriever = RAGRetriever()

    exploration: dict[str, Any] = {
        "base_url": url,
        "modules_discovered": [],
        "pages": [],
        "discrepancies": [],
    }

    async with PlaywrightClient() as client:
        # Login
        await client.navigate(url)
        try:
            await perform_login(client)
        except Exception as e:
            # Login failed or already logged in
            pass

        # Capture Dashboard / landing state
        dashboard_state = await _capture_page_state(client, "Dashboard", "dashboard", retriever)
        exploration["pages"].append(dashboard_state)

        # Discover navigation modules
        nav_links = await _discover_nav_modules(client)
        exploration["nav_modules"] = nav_links

        for mod in nav_links:
            mod_name = mod["label"]
            if target_module and target_module.lower() not in mod_name.lower():
                continue

            cov = retriever.get_coverage_status(mod_name)
            doc_status = cov.get("status", "UNDOCUMENTED")
            memory = ModuleMemoryStore(mod_name)

            mod_entry = {
                "module": mod_name,
                "doc_status": doc_status,
                "selector": mod["selector"],
                "href": mod.get("href", ""),
                "pages": [],
            }

            try:
                client.clear_logs()
                await client.click(mod["selector"])
                await client.wait_for_network_idle()

                # Take exploration screenshot
                screenshot_name = f"explore_{memory.module_key}"
                screenshot_path = await client.screenshot(screenshot_name)

                # Capture page details & interactive elements
                page_data = await _capture_page_state(
                    client,
                    label=mod_name,
                    module_name=mod_name,
                    retriever=retriever,
                    screenshot_path=str(screenshot_path),
                )
                mod_entry["pages"].append(page_data)
                exploration["pages"].append(page_data)

                # Update module persistent memory
                memory.add_or_update_page(page_data)

                # Record API calls observed
                for net in client.get_network_logs():
                    if net.get("type") == "response":
                        memory.record_api_call(
                            method="GET",  # Default or extracted
                            url=net.get("url", ""),
                            status=net.get("status", 200),
                            action=f"Navigate to {mod_name}",
                        )

                # Check for discrepancies against reference docs
                if doc_status == "DOCUMENTED":
                    doc_chunks = retriever.retrieve_relevant_chunks(mod_name, module_name=mod_name, max_chunks=1)
                    if doc_chunks:
                        expected_elements = doc_chunks[0].get("elements", [])
                        observed_elements = [el.get("text", "") for el in page_data.get("interactive_elements", [])]
                        for exp in expected_elements[:3]:
                            if not any(exp.lower() in obs.lower() for obs in observed_elements if obs):
                                disc_title = f"Potential missing element in {mod_name}: '{exp}'"
                                memory.record_discrepancy(
                                    title=disc_title,
                                    documented_expectation=f"Docs mention element: {exp}",
                                    actual_behavior=f"Element not immediately visible on {page_data['url']}",
                                    evidence={"url": page_data["url"], "screenshot": str(screenshot_path)},
                                )
                                exploration["discrepancies"].append({
                                    "module": mod_name,
                                    "title": disc_title,
                                })

            except Exception as exc:
                mod_entry["error"] = str(exc)

            exploration["modules_discovered"].append(mod_entry)

    return exploration


async def _capture_page_state(
    client: PlaywrightClient,
    label: str,
    module_name: str,
    retriever: RAGRetriever,
    screenshot_path: str = "",
) -> dict[str, Any]:
    """Capture current page state, selectors, and interactive elements."""
    cov = retriever.get_coverage_status(module_name)
    elements = await client.extract_interactive_elements()
    selectors_map = {el["text"]: el["selector"] for el in elements if el.get("text") and len(el["text"]) < 40}

    return {
        "label": label,
        "module": module_name,
        "doc_status": cov.get("status", "UNDOCUMENTED"),
        "url": await client.get_url(),
        "title": await client.get_title(),
        "interactive_elements": elements[:25],
        "selectors": selectors_map,
        "screenshot": screenshot_path,
        "dom_snippet": (await client.get_dom_snapshot())[:2500],
    }


async def _discover_nav_modules(client: PlaywrightClient) -> list[dict[str, Any]]:
    """Discover top-level navigation items (Inventory, Sales, Purchases, Audits, Reports, etc.)."""
    nav_links: list[dict[str, Any]] = []
    try:
        elements = await client.page.query_selector_all("nav a, [role='navigation'] a, aside a, .sidebar a")
        for el in elements[:20]:
            text = (await el.text_content() or "").strip()
            href = await el.get_attribute("href") or ""
            if text and len(text) < 30 and not any(n["label"] == text for n in nav_links):
                nav_links.append({"label": text, "href": href, "selector": f"text={text}"})
    except Exception:
        pass

    # Fallback to standard canonical modules if nav elements are not found
    if not nav_links:
        for mod in ["Inventory", "Audit", "Performing Audit", "Sales", "Purchases", "Reports", "Setup"]:
            nav_links.append({"label": mod, "href": f"/{mod.lower().replace(' ', '-')}", "selector": f"text={mod}"})

    return nav_links
