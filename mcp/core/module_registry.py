"""
mcp/core/module_registry.py — Business module registration and discovery.

Modules self-register at import time.  The orchestrator looks them up by
name to run the appropriate pipeline.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp.modules.base_module import BaseModule


class ModuleRegistry:
    """Singleton registry for business modules."""

    def __init__(self) -> None:
        self._modules: dict[str, "BaseModule"] = {}

    def register(self, module: "BaseModule") -> None:
        """Register a module instance by its name (lowercased)."""
        key = module.name.lower()
        self._modules[key] = module

    def get(self, name: str) -> "BaseModule":
        """Retrieve a registered module by name (case-insensitive)."""
        key = name.lower()
        if key not in self._modules:
            available = ", ".join(sorted(self._modules)) or "(none)"
            raise KeyError(
                f"Module '{name}' is not registered. "
                f"Available modules: {available}"
            )
        return self._modules[key]

    def list_modules(self) -> list[str]:
        """Return sorted list of registered module names."""
        return sorted(self._modules)

    def has(self, name: str) -> bool:
        return name.lower() in self._modules

    def all(self) -> dict[str, "BaseModule"]:
        """Return a shallow copy of all registered modules."""
        return dict(self._modules)

    def __repr__(self) -> str:
        return f"ModuleRegistry(modules={self.list_modules()})"


# Global singleton — import and use directly.
module_registry = ModuleRegistry()
