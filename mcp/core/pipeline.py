"""
mcp/core/pipeline.py — Standard 12-step QA pipeline definition.

Every business module (Audit, Inventory, Finance, future modules) follows
the same pipeline.  Only module-specific workflows and business rules
change; the pipeline engine itself is generic and reusable.
"""

from __future__ import annotations

from enum import Enum, auto
from typing import Any


class PipelineStage(Enum):
    """The twelve canonical stages of the autonomous QA pipeline."""

    EXPLORE = auto()
    DISCOVER = auto()
    UNDERSTAND = auto()
    LOAD_DOCUMENTATION = auto()
    GENERATE_TESTS = auto()
    EXECUTE_TESTS = auto()
    VALIDATE_RESULTS = auto()
    CAPTURE_EVIDENCE = auto()
    DETECT_DEFECTS = auto()
    GENERATE_DEFECT_REPORTS = auto()
    GENERATE_TEST_REPORTS = auto()
    UPDATE_MEMORY = auto()


# Ordered sequence used by the orchestrator.
STANDARD_PIPELINE: list[PipelineStage] = list(PipelineStage)


class StageResult:
    """Outcome produced by a single pipeline stage execution."""

    __slots__ = ("stage", "status", "data", "error", "skipped_reason")

    def __init__(
        self,
        stage: PipelineStage,
        *,
        status: str = "SUCCESS",
        data: dict[str, Any] | None = None,
        error: str | None = None,
        skipped_reason: str | None = None,
    ) -> None:
        self.stage = stage
        self.status = status          # SUCCESS | FAILED | SKIPPED
        self.data = data or {}
        self.error = error
        self.skipped_reason = skipped_reason

    def is_success(self) -> bool:
        return self.status == "SUCCESS"

    def __repr__(self) -> str:
        return f"StageResult({self.stage.name}, status={self.status})"
