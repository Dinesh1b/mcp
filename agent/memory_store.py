"""
agent/memory_store.py — Persistent Module Memory Store.

Implements Phase 3: Persistent Module Memory.
One state store per module under modules/<module-name>/state.json:
- setup-and-configuration (documented)
- audit (documented)
- performing-audit (documented)
- inventory (documented)
- sales (undocumented — exploratory only)
- purchases (undocumented — exploratory only)
- reports (undocumented — exploratory only)

Stores:
- pages, selectors, APIs, known workflows/test cases
- prior results, known failures, screenshots
- expected vs. actual behavior
- doc-coverage status (DOCUMENTED / UNDOCUMENTED)
- doc-vs-app discrepancies
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from config.settings import settings
from knowledge.rag_retriever import RAGRetriever


class ModuleMemoryStore:
    """Manages persistent state for a specific application module."""

    def __init__(self, module_name: str):
        self.raw_module_name = module_name
        self.module_key = self._normalize_name(module_name)
        self.module_dir = settings.modules_dir / self.module_key
        self.module_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.module_dir / "state.json"

        self.retriever = RAGRetriever()
        cov = self.retriever.get_coverage_status(self.module_key)
        self.doc_status = cov.get("status", "UNDOCUMENTED")

        self.state: dict[str, Any] = self._load_state()

    @staticmethod
    def _normalize_name(name: str) -> str:
        norm = name.lower().strip().replace(" ", "-").replace("_", "-")
        # Match against known canonical names
        for canonical in [
            "setup-and-configuration",
            "audit",
            "performing-audit",
            "inventory",
            "sales",
            "purchases",
            "reports",
            "getting-started",
        ]:
            if canonical in norm or norm in canonical:
                return canonical
        return norm

    def _load_state(self) -> dict[str, Any]:
        """Load state from disk or initialize default schema."""
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        return {
            "module_name": self.module_key,
            "doc_status": self.doc_status,
            "last_updated": datetime.now().isoformat(),
            "pages": [],
            "selectors": {},
            "apis": [],
            "known_flows": [],
            "prior_results": [],
            "known_failures": [],
            "discrepancies": [],
        }

    def save(self) -> None:
        """Persist state to disk immediately."""
        self.state["last_updated"] = datetime.now().isoformat()
        self.state_file.write_text(json.dumps(self.state, indent=2, default=str), encoding="utf-8")

    # ── Selectors & Pages ─────────────────────────────────────────────────────

    def add_or_update_page(self, page_data: dict[str, Any]) -> None:
        """Add or update a page structure and merge its selectors."""
        url = page_data.get("url") or ""
        existing = next((p for p in self.state["pages"] if p.get("url") == url), None)
        if existing:
            existing.update(page_data)
        else:
            self.state["pages"].append(page_data)

        # Merge selectors
        if "selectors" in page_data:
            self.state["selectors"].update(page_data["selectors"])
        self.save()

    def get_selector(self, name: str) -> Optional[str]:
        """Retrieve known selector from memory."""
        return self.state.get("selectors", {}).get(name)

    # ── APIs ──────────────────────────────────────────────────────────────────

    def record_api_call(self, method: str, url: str, status: int, action: str = "") -> None:
        """Record an observed API endpoint mapping."""
        api_entry = {
            "method": method.upper(),
            "url": url,
            "status": status,
            "triggering_action": action,
            "timestamp": datetime.now().isoformat(),
        }
        # Avoid duplicate identical records
        if not any(a.get("method") == api_entry["method"] and a.get("url") == api_entry["url"] for a in self.state["apis"]):
            self.state["apis"].append(api_entry)
            self.save()

    # ── Discrepancies & Findings ──────────────────────────────────────────────

    def record_discrepancy(
        self,
        title: str,
        documented_expectation: str,
        actual_behavior: str,
        evidence: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Record a doc-vs-app discrepancy finding.
        Never silently resolve or guess.
        """
        discrepancy = {
            "title": title,
            "documented_expectation": documented_expectation,
            "actual_behavior": actual_behavior,
            "evidence": evidence or {},
            "recorded_at": datetime.now().isoformat(),
        }
        self.state["discrepancies"].append(discrepancy)
        self.save()

    # ── Test Results & Failures ───────────────────────────────────────────────

    def record_run_result(self, run_summary: dict[str, Any]) -> None:
        """Record a test execution run summary."""
        self.state["prior_results"].append(
            {
                "timestamp": datetime.now().isoformat(),
                "summary": run_summary,
            }
        )
        self.save()

    def record_failure(self, failure_detail: dict[str, Any]) -> None:
        """Record a confirmed failure / defect."""
        self.state["known_failures"].append(
            {
                "timestamp": datetime.now().isoformat(),
                "detail": failure_detail,
            }
        )
        self.save()

    def get_summary_for_llm(self) -> dict[str, Any]:
        """Produce a token-efficient summary for LLM context."""
        return {
            "module_name": self.module_key,
            "doc_status": self.doc_status,
            "page_count": len(self.state.get("pages", [])),
            "known_selectors": list(self.state.get("selectors", {}).keys())[:15],
            "known_apis": [f"{a.get('method')} {a.get('url')}" for a in self.state.get("apis", [])][:10],
            "discrepancies_count": len(self.state.get("discrepancies", [])),
            "recent_discrepancies": self.state.get("discrepancies", [])[-3:],
        }
