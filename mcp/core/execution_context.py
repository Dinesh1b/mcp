"""
mcp/core/execution_context.py — Per-run context object.

Carries all run-level state through the pipeline so that every agent and
service can read/write shared data without tight coupling.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from config.settings import settings


@dataclass
class ExecutionContext:
    """Immutable-ish bag of state for a single pipeline run."""

    # ── Identity ──────────────────────────────────────────────────────────
    module_name: str
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: str = field(
        default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S")
    )

    # ── Application ───────────────────────────────────────────────────────
    base_url: str = field(default_factory=lambda: settings.base_url)

    # ── Accumulated data (written by stages, read by later stages) ───────
    exploration_data: dict[str, Any] = field(default_factory=dict)
    discovered_pages: list[dict[str, Any]] = field(default_factory=list)
    module_documentation: dict[str, Any] = field(default_factory=dict)
    test_plan: dict[str, Any] = field(default_factory=dict)
    test_results: list[dict[str, Any]] = field(default_factory=list)
    defects: list[dict[str, Any]] = field(default_factory=list)
    evidence_paths: list[str] = field(default_factory=list)
    memory_snapshot: dict[str, Any] = field(default_factory=dict)

    # ── Pipeline tracking ─────────────────────────────────────────────────
    completed_stages: list[str] = field(default_factory=list)
    stage_errors: dict[str, str] = field(default_factory=dict)

    # ── Paths ─────────────────────────────────────────────────────────────
    @property
    def evidence_dir(self) -> Path:
        return settings.evidence_dir

    @property
    def report_dir(self) -> Path:
        return settings.report_dir

    @property
    def defects_dir(self) -> Path:
        d = settings.project_root / "defects"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def memory_dir(self) -> Path:
        d = settings.project_root / "module_memory" / self.module_name
        d.mkdir(parents=True, exist_ok=True)
        return d

    # ── Summary helpers ───────────────────────────────────────────────────
    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.test_results if r.get("status") == "PASS")

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.test_results if r.get("status") == "FAIL")

    @property
    def blocked_count(self) -> int:
        return sum(1 for r in self.test_results if r.get("status") == "BLOCKED")

    @property
    def skipped_count(self) -> int:
        return sum(1 for r in self.test_results if r.get("status") == "SKIPPED")

    @property
    def total_count(self) -> int:
        return len(self.test_results)

    def mark_stage_complete(self, stage_name: str) -> None:
        if stage_name not in self.completed_stages:
            self.completed_stages.append(stage_name)

    def mark_stage_error(self, stage_name: str, error: str) -> None:
        self.stage_errors[stage_name] = error

    def to_dict(self) -> dict[str, Any]:
        """Serialize for JSON / reporting."""
        return {
            "module_name": self.module_name,
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "base_url": self.base_url,
            "total_tests": self.total_count,
            "passed": self.passed_count,
            "failed": self.failed_count,
            "blocked": self.blocked_count,
            "skipped": self.skipped_count,
            "defect_count": len(self.defects),
            "evidence_count": len(self.evidence_paths),
            "completed_stages": self.completed_stages,
            "stage_errors": self.stage_errors,
        }
