"""
workflows/login.py — Reusable authentication workflow.

Login once → save storage state → reuse for all module tests.
Credentials come from environment variables only.
"""

from __future__ import annotations

from pathlib import Path

from mcp.playwright_client import PlaywrightClient
from config.settings import settings

AUTH_STATE_PATH = Path(__file__).parent.parent / ".auth_state.json"


async def perform_login(client: PlaywrightClient) -> None:
    """
    Perform login using credentials from environment variables.
    Detects common login form patterns automatically.
    """
    if not settings.qa_username or not settings.qa_password:
        raise EnvironmentError(
            "QA_USERNAME and QA_PASSWORD must be set in environment / .env file."
        )

    # Try common username field selectors
    username_selectors = [
        "input[name='username']",
        "input[name='email']",
        "input[type='email']",
        "input[id='username']",
        "input[placeholder*='email' i]",
        "input[placeholder*='username' i]",
    ]
    password_selectors = [
        "input[name='password']",
        "input[type='password']",
        "input[id='password']",
    ]
    submit_selectors = [
        "button[type='submit']",
        "input[type='submit']",
        "button:has-text('Login')",
        "button:has-text('Sign In')",
        "button:has-text('Log In')",
    ]

    for sel in username_selectors:
        try:
            await client.page.wait_for_selector(sel, timeout=3000)
            await client.fill(sel, settings.qa_username)
            break
        except Exception:
            continue

    for sel in password_selectors:
        try:
            await client.page.wait_for_selector(sel, timeout=3000)
            await client.fill(sel, settings.qa_password)
            break
        except Exception:
            continue

    for sel in submit_selectors:
        try:
            await client.page.wait_for_selector(sel, timeout=3000)
            await client.click(sel)
            break
        except Exception:
            continue

    # Wait for navigation away from login page
    await client.wait_for_network_idle()


async def save_auth_state(client: PlaywrightClient) -> None:
    """Save authenticated browser storage state for reuse."""
    await client.save_storage_state(AUTH_STATE_PATH)


async def create_authenticated_client() -> PlaywrightClient:
    """Create a PlaywrightClient with existing auth state if available."""
    if AUTH_STATE_PATH.exists():
        return PlaywrightClient(storage_state=AUTH_STATE_PATH)
    return PlaywrightClient()
