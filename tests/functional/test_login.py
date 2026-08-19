"""
tests/functional/test_login.py — Login functional tests.
"""

import pytest
from config.settings import settings


@pytest.mark.functional
async def test_login_page_loads(page):
    """Verify that the login page loads successfully."""
    await page.goto(settings.base_url)
    assert await page.title() != "", "Page title should not be empty"


@pytest.mark.functional
async def test_successful_login(authenticated_page):
    """Verify that authentication succeeds and user is redirected."""
    current_url = authenticated_page.url
    assert "login" not in current_url.lower(), (
        f"Expected to be redirected away from login page, but URL is: {current_url}"
    )


@pytest.mark.negative
async def test_login_invalid_credentials(page):
    """Verify that invalid credentials produce an error message."""
    await page.goto(settings.base_url)

    # Fill with invalid credentials
    for sel in ["input[name='username']", "input[name='email']", "input[type='email']"]:
        try:
            await page.wait_for_selector(sel, timeout=2000)
            await page.fill(sel, "invalid_user@test.invalid")
            break
        except Exception:
            continue

    for sel in ["input[name='password']", "input[type='password']"]:
        try:
            await page.wait_for_selector(sel, timeout=2000)
            await page.fill(sel, "wrongpassword123")
            break
        except Exception:
            continue

    for sel in ["button[type='submit']", "button:has-text('Login')", "button:has-text('Sign In')"]:
        try:
            await page.wait_for_selector(sel, timeout=2000)
            await page.click(sel)
            break
        except Exception:
            continue

    await page.wait_for_load_state("networkidle")

    # Verify: error message shown OR still on login page
    still_on_login = "login" in page.url.lower()
    error_visible = await page.is_visible("[role='alert'], .error, .alert-error, text=Invalid") 
    
    assert still_on_login or error_visible, (
        "Expected an error message or to remain on login page after invalid credentials"
    )
