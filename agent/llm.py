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

    if provider == "gemini" or provider == "google":
        return await _call_gemini(system=system, user=user, max_tokens=max_tokens)
    elif provider == "openai":
        return await _call_openai(system=system, user=user, max_tokens=max_tokens)
    elif provider == "anthropic":
        return await _call_anthropic(system=system, user=user, max_tokens=max_tokens)
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: '{provider}'. Use 'gemini', 'openai', or 'anthropic'.")


async def _call_gemini(system: str, user: str, max_tokens: int) -> str:
    """Call Google Gemini API."""
    if not settings.gemini_api_key:
        raise EnvironmentError("GEMINI_API_KEY / GOOGLE_API_KEY is not set.")

    # Try modern google-genai or google-generativeai SDK
    try:
        from google import genai
        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(
            model=settings.llm_model or "gemini-2.5-flash",
            contents=f"System instructions:\n{system}\n\nUser request:\n{user}",
        )
        return response.text or ""
    except ImportError:
        pass

    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(
            model_name=settings.llm_model or "gemini-2.5-flash",
            system_instruction=system,
        )
        response = await model.generate_content_async(user)
        return response.text or ""
    except ImportError:
        pass

    # Fallback to direct HTTP request using urllib
    import urllib.request
    import json

    model_name = settings.llm_model or "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={settings.gemini_api_key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"System instructions:\n{system}\n\nUser request:\n{user}"}
                ]
            }
        ],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": 0.1,
        }
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        candidates = data.get("candidates", [])
        if candidates and "content" in candidates[0]:
            parts = candidates[0]["content"].get("parts", [])
            return "".join(p.get("text", "") for p in parts)
        return ""


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

