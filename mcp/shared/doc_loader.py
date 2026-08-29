"""
mcp/shared/doc_loader.py — Documentation and expected behavior loader.

Loads module-specific expected behaviors from mcp/modules/<module>/docs.py.
Supports the distinction between:
  - Expected Behavior (from documentation)
  - Observed Behavior (from previous runs / memory)
  - Actual Behavior (from current execution)
"""

from __future__ import annotations

import importlib
from typing import Any


def load_module_docs(module_name: str) -> dict[str, Any]:
    """
    Load documented expected behaviors for a module.

    Attempts to import mcp.modules.<module_name>.docs and call
    get_expected_behaviors().  Returns empty dict on failure.

    Returns:
        Dict with keys like 'expected_behaviors', 'business_rules', etc.
    """
    try:
        mod = importlib.import_module(f"mcp.modules.{module_name}.docs")
        if hasattr(mod, "get_expected_behaviors"):
            return mod.get_expected_behaviors()
        return {}
    except (ImportError, ModuleNotFoundError):
        return {}


def get_expected_behavior(
    module_name: str,
    workflow: str,
) -> dict[str, Any] | None:
    """
    Get the expected behavior for a specific workflow within a module.

    Returns:
        Dict describing expected behavior, or None if not documented.
    """
    docs = load_module_docs(module_name)
    behaviors = docs.get("expected_behaviors", {})
    return behaviors.get(workflow)


def classify_behavior_source(
    has_documentation: bool,
    has_memory: bool,
) -> str:
    """
    Determine the source of expected behavior.

    Returns:
        'documented' | 'observed' | 'unknown'
    """
    if has_documentation:
        return "documented"
    elif has_memory:
        return "observed"
    return "unknown"
