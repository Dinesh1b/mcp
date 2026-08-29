"""
mcp/core/routing.py — Dynamic URL and route resolution for the MCP QA Platform.

Eliminates hardcoded hostnames and handles path vs hash routing dynamically.
"""

from __future__ import annotations

from urllib.parse import urlparse, urljoin
from config.settings import settings


def resolve_module_url(base_url: str | None, route: str) -> str:
    """
    Resolve a module or feature route relative to the target application's base URL.

    Handles:
    - Base URLs with hash fragments (e.g. https://domain.com/#/home/purchase/newpurchase)
    - Path-based SPA routing (e.g. https://domain.com/home/audit)
    - Full URLs passed as routes (returns route unmodified)

    Args:
        base_url: Base application URL (e.g. from ExecutionContext.base_url or settings.base_url).
        route: Target module path (e.g. '/home/audit', 'home/inventory', '#/home/purchase').

    Returns:
        Fully qualified target URL.
    """
    if route.startswith("http://") or route.startswith("https://"):
        return route

    base = (base_url or settings.base_url).strip()
    parsed_base = urlparse(base)

    # Origin without hash or path: e.g. "https://yellow-river-0ebeae800.2.azurestaticapps.net"
    origin = f"{parsed_base.scheme}://{parsed_base.netloc}"

    clean_route = route.lstrip("/")

    # If the target application uses hash-based routing in its base URL
    if "#" in base and not clean_route.startswith("#"):
        # e.g. base has "#/home/purchase", target route is "home/audit" -> "https://origin/#/home/audit"
        return f"{origin}/#/{clean_route}"

    if clean_route.startswith("#"):
        return f"{origin}/{clean_route}"

    return f"{origin}/{clean_route}"
