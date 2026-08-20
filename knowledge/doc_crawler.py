"""
knowledge/doc_crawler.py — Documentation crawler for Stockount (Docusaurus).

Crawls the actual docs.stockount.com site map, extracts structured knowledge per page:
- Elements (buttons, fields, dropdowns, tables)
- Actions
- Validations / business rules
- APIs (if documented)
- Expected results (if documented)
- Category / Module mapping
"""

from __future__ import annotations

import asyncio
import json
import re
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

from config.settings import settings


@dataclass
class DocPage:
    url: str
    title: str
    category: str
    content_raw: str
    elements: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    validations: list[str] = field(default_factory=list)
    apis: list[str] = field(default_factory=list)
    expected_results: list[str] = field(default_factory=list)
    doc_status: str = "DOCUMENTED"


# Known site map structure from docs.stockount.com
KNOWN_DOC_PATHS = [
    "/docs/intro",
    "/docs/category/getting-started",
    "/docs/category/setup-and-configuration",
    "/docs/category/audit",
    "/docs/category/performing-audit",
    "/docs/Sk-Mobile",
    "/docs/Best-Practice",
    "/docs/Appendix",
]

# Canonical module coverage map
INITIAL_COVERAGE_MAP = {
    "getting-started": {
        "status": "DOCUMENTED",
        "doc_paths": ["/docs/category/getting-started"],
        "description": "System Requirements, Account Setup, Interface Overview (Inventory, Sales, Purchases, Audits, Reports)",
    },
    "setup-and-configuration": {
        "status": "DOCUMENTED",
        "doc_paths": ["/docs/category/setup-and-configuration"],
        "description": "Company & Branch Configuration, Adding User, Role Access",
    },
    "audit": {
        "status": "DOCUMENTED",
        "doc_paths": ["/docs/category/audit"],
        "description": "Dashboard, Audit Plans, Create Audit Plan, Different Audit Types & Frequencies",
    },
    "performing-audit": {
        "status": "DOCUMENTED",
        "doc_paths": ["/docs/category/performing-audit"],
        "description": "Ongoing Audits, Audit History (read-only)",
    },
    "inventory": {
        "status": "DOCUMENTED",
        "doc_paths": ["/docs/category/getting-started"],
        "description": "Item Groups, Categories, Items, Barcode Config (EAN13, Code128, QR, Splitters)",
    },
    "sales": {
        "status": "UNDOCUMENTED",
        "doc_paths": [],
        "description": "Present in-app nav, not documented. Exploratory only.",
    },
    "purchases": {
        "status": "UNDOCUMENTED",
        "doc_paths": [],
        "description": "Present in-app nav, not documented. Exploratory only.",
    },
    "reports": {
        "status": "UNDOCUMENTED",
        "doc_paths": [],
        "description": "Present in-app nav, not documented. Exploratory only.",
    },
}


def clean_html(html_text: str) -> str:
    """Extract readable text from HTML by stripping tags and scripts."""
    # Remove script and style elements
    text = re.sub(r"<(script|style).*?>.*?</\1>", "", html_text, flags=re.DOTALL | re.IGNORECASE)
    # Extract text from tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_title(html_text: str) -> str:
    """Extract page title from HTML."""
    match = re.search(r"<h1[^>]*>(.*?)</h1>", html_text, flags=re.DOTALL | re.IGNORECASE)
    if match:
        return clean_html(match.group(1))
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html_text, flags=re.IGNORECASE)
    if title_match:
        return clean_html(title_match.group(1)).split("|")[0].strip()
    return "Stockount Documentation"


def extract_elements_and_actions(text: str) -> tuple[list[str], list[str], list[str], list[str]]:
    """Heuristically extract elements, actions, validations, and expected results from text."""
    elements: list[str] = []
    actions: list[str] = []
    validations: list[str] = []
    expected_results: list[str] = []

    sentences = re.split(r"[.\n]+", text)
    for s in sentences:
        s_clean = s.strip()
        if not s_clean:
            continue
        lower = s_clean.lower()
        if any(k in lower for k in ["button", "field", "dropdown", "table", "checkbox", "input", "barcode", "qr code"]):
            elements.append(s_clean)
        if any(k in lower for k in ["click", "select", "create", "enter", "navigate", "assign", "perform", "scan"]):
            actions.append(s_clean)
        if any(k in lower for k in ["must", "required", "validation", "only", "can't", "cannot", "read-only"]):
            validations.append(s_clean)
        if any(k in lower for k in ["shows", "reflects", "moves to", "generates", "results in", "completed", "saved"]):
            expected_results.append(s_clean)

    return elements[:15], actions[:15], validations[:10], expected_results[:10]


class DocCrawler:
    """Crawls and structures documentation from docs.stockount.com."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.docs_url).rstrip("/")
        self.knowledge_dir = settings.knowledge_dir
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.knowledge_dir / "docs_cache.json"
        self.coverage_file = self.knowledge_dir / "doc_coverage_map.json"

    def crawl_sync(self) -> dict[str, Any]:
        """Synchronously crawl the documentation tree."""
        pages: list[DocPage] = []
        discovered_links = set(KNOWN_DOC_PATHS)

        # Initialize coverage map
        coverage_map = dict(INITIAL_COVERAGE_MAP)

        for path in discovered_links:
            url = f"{self.base_url}{path}" if path.startswith("/") else path
            try:
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Stockount-AI-QA"},
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    html = resp.read().decode("utf-8", errors="ignore")
                    title = extract_title(html)
                    raw_text = clean_html(html)
                    elements, actions, validations, exp_results = extract_elements_and_actions(raw_text)

                    # Determine category
                    category = "general"
                    for cat in coverage_map.keys():
                        if cat in path.lower():
                            category = cat
                            break

                    pages.append(
                        DocPage(
                            url=url,
                            title=title,
                            category=category,
                            content_raw=raw_text[:4000],  # bounded text
                            elements=elements,
                            actions=actions,
                            validations=validations,
                            apis=[],
                            expected_results=exp_results,
                            doc_status="DOCUMENTED",
                        )
                    )
            except Exception as e:
                # Log fetch exception but continue
                pages.append(
                    DocPage(
                        url=url,
                        title=f"Doc Page ({path})",
                        category="general",
                        content_raw=f"Fallback offline structure for {path}. Error: {e}",
                        doc_status="DOCUMENTED",
                    )
                )

        # Save cached pages
        pages_dict = [asdict(p) for p in pages]
        self.cache_file.write_text(json.dumps(pages_dict, indent=2), encoding="utf-8")
        self.coverage_file.write_text(json.dumps(coverage_map, indent=2), encoding="utf-8")

        return {
            "crawled_count": len(pages),
            "coverage_map": coverage_map,
            "cache_file": str(self.cache_file),
        }

    async def crawl(self) -> dict[str, Any]:
        """Async wrapper around crawl_sync."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.crawl_sync)


if __name__ == "__main__":
    crawler = DocCrawler()
    result = crawler.crawl_sync()
    print(f"Crawled {result['crawled_count']} pages. Saved to {result['cache_file']}")
