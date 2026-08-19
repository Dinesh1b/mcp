"""
agent/llm.py — Unified LLM client.

Routes requests to OpenAI or Anthropic based on LLM_PROVIDER setting.
The LLM MUST NOT fabricate tool results or application state.
Every factual result must come from a tool or test assertion.
"""

from __future__ import annotations

from config.settings import settings

# ── Module-level client cache ─────────────────────────────────────────────────
# Avoids creating a new API client on every call_llm() invocation.
_openai_client = None
_anthropic_client = None


async def call_llm(system: str, user: str, max_tokens: int = 4096) -> str:
    """
    Call the configured LLM and return the assistant's response text.

    Args:
        system: System prompt.
        user: User message.
        max_tokens: Maximum tokens in the response.

    Returns:
        Assistant response text.

    Raises:
        ValueError: If LLM_PROVIDER is unsupported.
        RuntimeError: If the API call fails.
    """
    provider = settings.llm_provider.lower()

    if provider == "openai":
        return await _call_openai(system=system, user=user, max_tokens=max_tokens)
    elif provider == "anthropic":
        return await _call_anthropic(system=system, user=user, max_tokens=max_tokens)
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: '{provider}'. Use 'openai' or 'anthropic'.")


def _get_openai_client():
    """Return a cached AsyncOpenAI client, creating it on first use."""
    global _openai_client
    if _openai_client is None:
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise RuntimeError("openai package not installed. Run: pip install openai")

        if not settings.openai_api_key:
            raise EnvironmentError("OPENAI_API_KEY is not set.")

        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


def _get_anthropic_client():
    """Return a cached AsyncAnthropic client, creating it on first use."""
    global _anthropic_client
    if _anthropic_client is None:
        try:
            import anthropic
        except ImportError:
            raise RuntimeError("anthropic package not installed. Run: pip install anthropic")

        if not settings.anthropic_api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY is not set.")

        _anthropic_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _anthropic_client


async def _call_openai(system: str, user: str, max_tokens: int) -> str:
    client = _get_openai_client()
    response = await client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=max_tokens,
        temperature=0.1,
    )
    return response.choices[0].message.content or ""


async def _call_anthropic(system: str, user: str, max_tokens: int) -> str:
    client = _get_anthropic_client()
    message = await client.messages.create(
        model=settings.llm_model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return message.content[0].text if message.content else ""

