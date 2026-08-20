"""
agent/repro_engine.py — Test Case & Bug Reproduction Engine.

Implements Phase 6:
Accepts:
- Plain English request ("Test the Audit Plan creation flow")
- Specific sequence ("Create Audit Plan -> Perform Audit -> Verify Audit History")
- Bug repro steps ("Login -> Click Audit -> Submit Empty Plan -> Notice 500 error")
- Uploaded test cases (CSV, JSON, Markdown, Plain Text)

Normalizes into:
Requirement -> Relevant Docs (or "none found") -> Known App State -> Test Plan -> Execution
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any, Optional

from knowledge.rag_retriever import RAGRetriever
from agent.memory_store import ModuleMemoryStore


class ReproductionEngine:
    """Parses and normalizes varied QA inputs into standardized test scenarios."""

    def __init__(self):
        self.retriever = RAGRetriever()

    def parse_input(
        self,
        raw_input: str,
        file_path: Optional[str | Path] = None,
    ) -> dict[str, Any]:
        """
        Normalize raw text, step sequence, or file content into a test plan structure.
        """
        if file_path:
            p = Path(file_path)
            if p.exists():
                ext = p.suffix.lower()
                content = p.read_text(encoding="utf-8")
                if ext == ".json":
                    return self._parse_json(content)
                elif ext == ".csv":
                    return self._parse_csv(content)
                elif ext in [".md", ".txt"]:
                    return self._parse_text_or_sequence(content)

        if "->" in raw_input or "→" in raw_input:
            return self._parse_sequence(raw_input)

        return self._parse_text_or_sequence(raw_input)

    def _parse_sequence(self, sequence_str: str) -> dict[str, Any]:
        """Parse step sequences like: Step 1 -> Step 2 -> Step 3"""
        steps = [s.strip() for s in sequence_str.replace("→", "->").split("->") if s.strip()]
        module_name = self._infer_module(sequence_str)
        cov = self.retriever.get_coverage_status(module_name)
        doc_status = cov.get("status", "UNDOCUMENTED")

        scenarios = []
        for i, step in enumerate(steps, 1):
            scenarios.append({
                "id": f"SEQ_{i:03d}",
                "title": step,
                "type": "sequence_step",
                "doc_status": doc_status,
                "preconditions": [],
                "steps": [f"Execute action: {step}"],
                "expected_result": f"Step '{step}' completes successfully." if doc_status == "DOCUMENTED" else "Observe behavior",
                "status": "PLANNED",
            })

        return {
            "module": module_name,
            "feature": "Step Sequence Execution",
            "doc_status": doc_status,
            "testing_types": ["sequential_workflow"],
            "scenarios": scenarios,
        }

    def _parse_csv(self, csv_text: str) -> dict[str, Any]:
        """Parse CSV test cases (id, title, steps, expected_result)."""
        reader = csv.DictReader(io.StringIO(csv_text))
        scenarios = []
        module_name = "Imported Module"
        for i, row in enumerate(reader, 1):
            title = row.get("title") or row.get("name") or f"Test Case {i}"
            mod = row.get("module") or module_name
            cov = self.retriever.get_coverage_status(mod)
            scenarios.append({
                "id": row.get("id") or f"CSV_{i:03d}",
                "title": title,
                "type": row.get("type", "functional"),
                "doc_status": cov.get("status", "UNDOCUMENTED"),
                "preconditions": [row.get("preconditions", "")] if row.get("preconditions") else [],
                "steps": [s.strip() for s in (row.get("steps") or "").split(";") if s.strip()],
                "expected_result": row.get("expected_result") or "Verify expected outcome",
                "status": "PLANNED",
            })
        return {
            "module": module_name,
            "feature": "CSV Test Cases",
            "testing_types": ["imported_csv"],
            "scenarios": scenarios,
        }

    def _parse_json(self, json_text: str) -> dict[str, Any]:
        """Parse JSON test plan."""
        data = json.loads(json_text)
        if isinstance(data, list):
            data = {"module": "Imported JSON", "scenarios": data}
        return data

    def _parse_text_or_sequence(self, text: str) -> dict[str, Any]:
        """Parse plain English request or bug repro."""
        module_name = self._infer_module(text)
        cov = self.retriever.get_coverage_status(module_name)
        doc_status = cov.get("status", "UNDOCUMENTED")

        # Basic default scenario
        return {
            "module": module_name,
            "feature": text[:60],
            "doc_status": doc_status,
            "testing_types": ["exploratory" if doc_status == "UNDOCUMENTED" else "functional"],
            "scenarios": [
                {
                    "id": "TC_001",
                    "title": text,
                    "type": "functional",
                    "doc_status": doc_status,
                    "preconditions": ["Logged in"],
                    "steps": [f"Execute workflow for: {text}"],
                    "expected_result": "Perform verification against live app state." if doc_status == "DOCUMENTED" else "Observe and record live app behavior.",
                    "status": "PLANNED",
                }
            ],
        }

    @staticmethod
    def _infer_module(text: str) -> str:
        lower = text.lower()
        if "audit" in lower:
            return "audit"
        elif "inventory" in lower or "item" in lower or "barcode" in lower:
            return "inventory"
        elif "setup" in lower or "user" in lower or "branch" in lower:
            return "setup-and-configuration"
        elif "sales" in lower:
            return "sales"
        elif "purchase" in lower:
            return "purchases"
        elif "report" in lower:
            return "reports"
        return "general"
