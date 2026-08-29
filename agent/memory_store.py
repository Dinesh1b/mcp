"""
agent/memory_store.py — Persistent Module Memory Store.

Implements Phase 3: Persistent Module Memory.
One state store per module under modules/<module-name>/:
- module-map.json
- state.json
- discovered-pages.json
- discovered-actions.json
- discovered-flows.json
Directories: test-cases/, evidence/, defects/, regression/
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
        
        # Create base directory and subdirectories
        self._ensure_directories()
        
        # File paths
        self.state_file = self.module_dir / "state.json"
        self.module_map_file = self.module_dir / "module-map.json"
        self.pages_file = self.module_dir / "discovered-pages.json"
        self.actions_file = self.module_dir / "discovered-actions.json"
        self.flows_file = self.module_dir / "discovered-flows.json"

        self.retriever = RAGRetriever()
        cov = self.retriever.get_coverage_status(self.module_key)
        self.doc_status = cov.get("status", "UNDOCUMENTED")

        # Load states
        self.state = self._load_json(self.state_file, self._default_state())
        self.module_map = self._load_json(self.module_map_file, {"menus": [], "submenus": [], "hierarchy": {}})
        self.pages = self._load_json(self.pages_file, [])
        self.actions = self._load_json(self.actions_file, [])
        self.flows = self._load_json(self.flows_file, [])

    def _ensure_directories(self) -> None:
        self.module_dir.mkdir(parents=True, exist_ok=True)
        for subdir in ["test-cases", "evidence", "defects", "regression"]:
            (self.module_dir / subdir).mkdir(exist_ok=True)

    @staticmethod
    def _normalize_name(name: str) -> str:
        norm = name.lower().strip().replace(" ", "-").replace("_", "-")
        for canonical in [
            "setup-and-configuration", "audit", "performing-audit",
            "inventory", "sales", "purchases", "reports", "getting-started",
        ]:
            if canonical in norm or norm in canonical:
                return canonical
        return norm

    def _load_json(self, path: Path, default: Any) -> Any:
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return default

    def _save_json(self, path: Path, data: Any) -> None:
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def _default_state(self) -> dict[str, Any]:
        return {
            "module_name": self.module_key,
            "doc_status": self.doc_status,
            "last_updated": datetime.now().isoformat(),
            "selectors": {},
            "apis": [],
            "prior_results": [],
            "known_failures": [],
            "discrepancies": [],
        }

    def save(self) -> None:
        """Persist all state immediately."""
        self.state["last_updated"] = datetime.now().isoformat()
        self._save_json(self.state_file, self.state)
        self._save_json(self.module_map_file, self.module_map)
        self._save_json(self.pages_file, self.pages)
        self._save_json(self.actions_file, self.actions)
        self._save_json(self.flows_file, self.flows)

    def detect_changes(self, new_pages: list[dict[str, Any]]) -> dict[str, Any]:
        """Compare new pages with currently saved pages to find diffs."""
        old_urls = {p.get("url") for p in self.pages if p.get("url")}
        new_urls = {p.get("url") for p in new_pages if p.get("url")}
        
        added = new_urls - old_urls
        removed = old_urls - new_urls
        
        return {
            "added_pages": list(added),
            "removed_pages": list(removed)
        }

    # ── Selectors & Pages ─────────────────────────────────────────────────────

    def add_or_update_page(self, page_data: dict[str, Any]) -> None:
        url = page_data.get("url") or ""
        existing = next((p for p in self.pages if p.get("url") == url), None)
        if existing:
            existing.update(page_data)
        else:
            self.pages.append(page_data)

        if "selectors" in page_data:
            self.state["selectors"].update(page_data["selectors"])
        self.save()

    def get_selector(self, name: str) -> Optional[str]:
        return self.state.get("selectors", {}).get(name)

    # ── Actions & Flows ───────────────────────────────────────────────────────

    def record_action(self, action_data: dict[str, Any]) -> None:
        self.actions.append(action_data)
        self.save()

    def record_flow(self, flow_data: dict[str, Any]) -> None:
        self.flows.append(flow_data)
        self.save()

    # ── APIs ──────────────────────────────────────────────────────────────────

    def record_api_call(self, method: str, url: str, status: int, action: str = "") -> None:
        api_entry = {
            "method": method.upper(),
            "url": url,
            "status": status,
            "triggering_action": action,
            "timestamp": datetime.now().isoformat(),
        }
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
        self.state["prior_results"].append(
            {
                "timestamp": datetime.now().isoformat(),
                "summary": run_summary,
            }
        )
        self.save()

    def record_failure(self, failure_detail: dict[str, Any]) -> None:
        self.state["known_failures"].append(
            {
                "timestamp": datetime.now().isoformat(),
                "detail": failure_detail,
            }
        )
        self.save()

    def get_summary_for_llm(self) -> dict[str, Any]:
        return {
            "module_name": self.module_key,
            "doc_status": self.doc_status,
            "page_count": len(self.pages),
            "known_selectors": list(self.state.get("selectors", {}).keys())[:15],
            "known_apis": [f"{a.get('method')} {a.get('url')}" for a in self.state.get("apis", [])][:10],
            "discrepancies_count": len(self.state.get("discrepancies", [])),
            "recent_discrepancies": self.state.get("discrepancies", [])[-3:],
            "flows_count": len(self.flows)
        }

