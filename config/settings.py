"""
config/settings.py — Environment-based configuration for AI QA Agent.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{key}' is not set. "
            "Check your .env file or environment."
        )
    return value


class Settings:
    """Central settings object. All values come from environment variables."""

    # ── Application Under Test ────────────────────────────────────────────────
    base_url: str = os.getenv("BASE_URL", "http://localhost:3000")
    docs_url: str = os.getenv("DOCS_URL", "https://docs.stockount.com")

    # ── Authentication ────────────────────────────────────────────────────────
    qa_username: str = os.getenv("QA_USERNAME", "")
    qa_password: str = os.getenv("QA_PASSWORD", "")

    # ── Browser ───────────────────────────────────────────────────────────────
    browser: str = os.getenv("BROWSER", "chromium")
    headless: bool = os.getenv("HEADLESS", "true").lower() == "true"
    timeout: int = int(os.getenv("TIMEOUT", "30000"))

    # ── Evidence ─────────────────────────────────────────────────────────────
    screenshot_on_failure: bool = (
        os.getenv("SCREENSHOT_ON_FAILURE", "true").lower() == "true"
    )
    video_on_failure: bool = os.getenv("VIDEO_ON_FAILURE", "true").lower() == "true"
    trace_on_retry: bool = os.getenv("TRACE_ON_RETRY", "true").lower() == "true"

    # ── LLM ──────────────────────────────────────────────────────────────────
    llm_provider: str = os.getenv("LLM_PROVIDER", "gemini")
    llm_model: str = os.getenv("LLM_MODEL", "gemini-2.5-flash")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")

    # ── Paths ─────────────────────────────────────────────────────────────────
    project_root: Path = Path(__file__).parent.parent
    report_dir: Path = project_root / os.getenv("REPORT_DIR", "reports")
    evidence_dir: Path = project_root / os.getenv("EVIDENCE_DIR", "evidence")
    test_data_dir: Path = project_root / "test-data"
    knowledge_dir: Path = project_root / "knowledge"
    modules_dir: Path = project_root / "modules"

    @classmethod
    def ensure_dirs(cls) -> None:
        """Create required output directories if they do not exist."""
        for subdir in ["screenshots", "traces", "videos", "console", "network"]:
            (cls.evidence_dir / subdir).mkdir(parents=True, exist_ok=True)
        cls.report_dir.mkdir(parents=True, exist_ok=True)
        cls.test_data_dir.mkdir(parents=True, exist_ok=True)
        cls.knowledge_dir.mkdir(parents=True, exist_ok=True)
        cls.modules_dir.mkdir(parents=True, exist_ok=True)
        # Ensure subdirectories for module stores
        for mod in [
            "setup-and-configuration",
            "audit",
            "performing-audit",
            "inventory",
            "sales",
            "purchases",
            "reports",
        ]:
            (cls.modules_dir / mod).mkdir(parents=True, exist_ok=True)


settings = Settings()
