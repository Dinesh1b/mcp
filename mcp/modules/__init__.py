"""
mcp/modules — Auto-registers all business modules into the ModuleRegistry.
"""

from mcp.core.module_registry import module_registry
from mcp.modules.base_module import BaseModule
from mcp.modules.audit.module import AuditModule
from mcp.modules.inventory.module import InventoryModule
from mcp.modules.finance.module import FinanceModule

# Register core business modules
module_registry.register(AuditModule())
module_registry.register(InventoryModule())
module_registry.register(FinanceModule())

__all__ = [
    "BaseModule",
    "AuditModule",
    "InventoryModule",
    "FinanceModule",
]
