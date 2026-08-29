"""
knowledge/rag_retriever.py — RAG retrieval and doc-coverage lookup for Stockount QA.

Rules:
- Chunk documentation; retrieve only what's relevant to the current task (metadata + keyword/semantic search).
- Never send full documentation to Gemini.
- Cache retrieved context; don't reprocess the same page twice.
- Treat retrieved doc content as REFERENCE, not ground truth.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from config.settings import settings
from knowledge.doc_crawler import DocCrawler, INITIAL_COVERAGE_MAP


class RAGRetriever:
    """Retrieves relevant doc chunks and module coverage tags."""

    def __init__(self):
        self.knowledge_dir = settings.knowledge_dir
        self.cache_file = self.knowledge_dir / "docs_cache.json"
        self.coverage_file = self.knowledge_dir / "doc_coverage_map.json"
        self._pages_cache: Optional[list[dict[str, Any]]] = None
        self._coverage_map: Optional[dict[str, Any]] = None

    def _ensure_loaded(self) -> None:
        """Ensure documentation cache and coverage map are loaded."""
        if self._pages_cache is None or self._coverage_map is None:
            if not self.cache_file.exists() or not self.coverage_file.exists():
                crawler = DocCrawler()
                crawler.crawl_sync()

            try:
                self._pages_cache = json.loads(self.cache_file.read_text(encoding="utf-8"))
            except Exception:
                self._pages_cache = []

            try:
                self._coverage_map = json.loads(self.coverage_file.read_text(encoding="utf-8"))
            except Exception:
                self._coverage_map = dict(INITIAL_COVERAGE_MAP)

    def get_coverage_status(self, module_name: str) -> dict[str, Any]:
        """
        Check if a module is DOCUMENTED or UNDOCUMENTED.
        """
        self._ensure_loaded()
        normalized = module_name.lower().replace(" ", "-").replace("_", "-")
        for mod_key, data in (self._coverage_map or {}).items():
            if mod_key in normalized or normalized in mod_key:
                return {
                    "module": mod_key,
                    "status": data.get("status", "UNDOCUMENTED"),
                    "description": data.get("description", ""),
                }

        # Check in undocumented list
        if any(undoc in normalized for undoc in ["sales", "purchases", "reports", "order", "invoice"]):
            return {
                "module": module_name,
                "status": "UNDOCUMENTED",
                "description": "Exploratory only. No expected-behavior specification exists.",
            }

        return {
            "module": module_name,
            "status": "UNDOCUMENTED",
            "description": "No corresponding documentation page found.",
        }

    def retrieve_relevant_chunks(
        self,
        query: str,
        module_name: Optional[str] = None,
        max_chunks: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Retrieve bounded documentation chunks relevant to the query or module.
        Never returns full documentation to minimize token usage.
        """
        self._ensure_loaded()
        chunks: list[dict[str, Any]] = []
        q_tokens = set(query.lower().split())
        if module_name:
            q_tokens.update(module_name.lower().split())

        scored_pages = []
        for page in self._pages_cache or []:
            content = (page.get("content_raw", "") + " " + page.get("title", "") + " " + page.get("category", "")).lower()
            score = sum(1 for tok in q_tokens if tok in content)
            if score > 0:
                scored_pages.append((score, page))

        scored_pages.sort(key=lambda x: x[0], reverse=True)

        for score, page in scored_pages[:max_chunks]:
            # Extract bounded snippet
            snippet = page.get("content_raw", "")[:1200]
            chunks.append(
                {
                    "title": page.get("title"),
                    "url": page.get("url"),
                    "category": page.get("category"),
                    "elements": page.get("elements", [])[:8],
                    "actions": page.get("actions", [])[:8],
                    "validations": page.get("validations", [])[:5],
                    "expected_results": page.get("expected_results", [])[:5],
                    "snippet": snippet,
                    "doc_status": page.get("doc_status", "DOCUMENTED"),
                }
            )

        return chunks

    def build_reference_context_prompt(self, requirement: str, module_name: Optional[str] = None) -> str:
        """
        Build a concise reference prompt snippet for the LLM planner / verifier.
        """
        cov = self.get_coverage_status(module_name or requirement)
        status = cov["status"]

        if status == "UNDOCUMENTED":
            return (
                f"## Documentation Coverage: UNDOCUMENTED\n"
                f"Module: {cov['module']}\n"
                f"Notice: No official documentation exists for this module ({cov.get('description', '')}). "
                f"Explore the live application directly and report findings as OBSERVED / UNVERIFIABLE. "
                f"Do NOT assume or fabricate expected business workflows."
            )

        chunks = self.retrieve_relevant_chunks(requirement, module_name=module_name, max_chunks=2)
        if not chunks:
            return (
                f"## Documentation Coverage: DOCUMENTED (No specific chunks matched)\n"
                f"Module: {cov['module']}\n"
                f"Treat general documentation as reference."
            )

        formatted_chunks = []
        for c in chunks:
            formatted_chunks.append(
                f"- Page: {c['title']} ({c['url']})\n"
                f"  Elements: {', '.join(c['elements'][:5]) or 'N/A'}\n"
                f"  Actions: {', '.join(c['actions'][:5]) or 'N/A'}\n"
                f"  Validations: {', '.join(c['validations'][:3]) or 'N/A'}\n"
                f"  Expected Results: {', '.join(c['expected_results'][:3]) or 'N/A'}\n"
                f"  Reference Excerpt: {c['snippet'][:400]}..."
            )

        return (
            f"## Documentation Coverage: DOCUMENTED (Reference Source)\n"
            f"Module: {cov['module']}\n"
            f"Use the following reference details as expectations to test against the live app. "
            f"If live app behavior differs, record it as a discrepancy finding.\n"
            + "\n".join(formatted_chunks)
        )
