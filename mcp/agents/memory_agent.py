"""
mcp/agents/memory_agent.py — Module Memory Agent.

Manages reading, persisting, and updating module-specific memory stores
(module_memory/<module>/memory.json).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TYPE_CHECKING
from datetime import datetime

from config.settings import settings

if TYPE_CHECKING:
    from mcp.core.execution_context import ExecutionContext


def get_memory_file_path(module_name: str) -> Path:
    """Return path to the memory JSON for a module."""
    mem_dir = settings.project_root / "module_memory" / module_name.lower()
    mem_dir.mkdir(parents=True, exist_ok=True)
    return mem_dir / "memory.json"


def load_memory(module_name: str) -> dict[str, Any]:
    """
    Load stored memory for the specified module.
    Returns default template if not yet initialized.
    """
    mem_file = get_memory_file_path(module_name)
    if mem_file.exists():
        try:
            return json.loads(mem_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    return {
        "module": module_name.lower(),
        "last_updated": None,
        "known_routes": [],
        "stable_selectors": {},
        "discovered_forms": [],
        "known_workflows": [],
        "known_defects": [],
        "execution_history": [],
    }


def update_memory(ctx: "ExecutionContext") -> Path:
    """
    Update the module memory with newly discovered information,
    test outcomes, and defects from the current execution context.
    """
    mem = load_memory(ctx.module_name)
    mem_file = get_memory_file_path(ctx.module_name)

    mem["last_updated"] = datetime.now().isoformat()

    # Update known routes
    routes = set(mem.get("known_routes", []))
    for page in ctx.exploration_data.get("pages", []):
        url = page.get("url")
        if url:
            routes.add(url)
    mem["known_routes"] = sorted(routes)

    # Append run history summary
    history = mem.get("execution_history", [])
    history.append({
        "run_id": ctx.run_id,
        "timestamp": ctx.timestamp,
        "total": ctx.total_count,
        "passed": ctx.passed_count,
        "failed": ctx.failed_count,
        "defects_found": len(ctx.defects),
    })
    mem["execution_history"] = history[-20:]  # keep last 20

    # Accumulate known defects
    existing_defect_ids = {d.get("defect_id") for d in mem.get("known_defects", [])}
    known_defects = mem.get("known_defects", [])
    for d in ctx.defects:
        if d.get("defect_id") not in existing_defect_ids:
            known_defects.append({
                "defect_id": d.get("defect_id"),
                "title": d.get("title"),
                "severity": d.get("severity"),
                "discovered_in_run": ctx.run_id,
            })
    mem["known_defects"] = known_defects

    mem_file.write_text(json.dumps(mem, indent=2, default=str), encoding="utf-8")
    return mem_file


async def run_memory_agent(ctx: "ExecutionContext") -> dict[str, Any]:
    """Agent interface wrapper for the memory agent."""
    path = update_memory(ctx)
    return {"status": "SUCCESS", "memory_path": str(path)}
