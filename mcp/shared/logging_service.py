"""
mcp/shared/logging_service.py — Structured execution logging.

Provides per-pipeline-run logging that captures stage transitions,
agent actions, and timing information.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, TYPE_CHECKING

from config.settings import settings

if TYPE_CHECKING:
    from mcp.core.execution_context import ExecutionContext


def get_run_logger(ctx: "ExecutionContext") -> logging.Logger:
    """
    Get or create a logger for a specific pipeline run.

    Logs are written to evidence/<module>_<run_id>.log.

    Returns:
        Configured Logger instance.
    """
    logger_name = f"mcp.{ctx.module_name}.{ctx.run_id}"
    logger = logging.getLogger(logger_name)

    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        # File handler
        log_dir = ctx.evidence_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{ctx.module_name}_{ctx.run_id}.log"

        fh = logging.FileHandler(str(log_file), encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger


def log_stage_start(ctx: "ExecutionContext", stage_name: str) -> None:
    """Log the start of a pipeline stage."""
    logger = get_run_logger(ctx)
    logger.info(f"STAGE START: {stage_name} | module={ctx.module_name} | run={ctx.run_id}")


def log_stage_end(
    ctx: "ExecutionContext",
    stage_name: str,
    status: str,
    data: dict[str, Any] | None = None,
) -> None:
    """Log the end of a pipeline stage."""
    logger = get_run_logger(ctx)
    logger.info(
        f"STAGE END: {stage_name} | status={status} | "
        f"data={json.dumps(data or {}, default=str)}"
    )


def log_action(ctx: "ExecutionContext", action: str, details: str = "") -> None:
    """Log a specific agent or workflow action."""
    logger = get_run_logger(ctx)
    logger.info(f"ACTION: {action} | {details}")


def log_error(ctx: "ExecutionContext", stage: str, error: str) -> None:
    """Log an error."""
    logger = get_run_logger(ctx)
    logger.error(f"ERROR in {stage}: {error}")
