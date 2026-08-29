"""
mcp/core/orchestrator.py — Top-level pipeline orchestrator.

Given a module name, runs the full 12-step pipeline using registered
agents, module workflows, and shared services.  This is the primary
entry point for programmatic pipeline execution.
"""

from __future__ import annotations

import sys
import traceback
from typing import Any

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from mcp.core.pipeline import PipelineStage, StageResult, STANDARD_PIPELINE
from mcp.core.execution_context import ExecutionContext
from mcp.core.module_registry import module_registry
from mcp.core.agent_registry import agent_registry
from mcp.core.workflow_engine import WorkflowEngine
from mcp.playwright_client import PlaywrightClient
from config.settings import settings
from workflows.login import perform_login

console = Console()


class Orchestrator:
    """
    Runs the standard QA pipeline for a given business module.

    Usage::

        orch = Orchestrator(module_name="audit")
        await orch.run()
    """

    # Maps PipelineStage → the method that executes it.
    _STAGE_HANDLERS: dict[PipelineStage, str] = {
        PipelineStage.EXPLORE: "_stage_explore",
        PipelineStage.DISCOVER: "_stage_discover",
        PipelineStage.UNDERSTAND: "_stage_understand",
        PipelineStage.LOAD_DOCUMENTATION: "_stage_load_documentation",
        PipelineStage.GENERATE_TESTS: "_stage_generate_tests",
        PipelineStage.EXECUTE_TESTS: "_stage_execute_tests",
        PipelineStage.VALIDATE_RESULTS: "_stage_validate_results",
        PipelineStage.CAPTURE_EVIDENCE: "_stage_capture_evidence",
        PipelineStage.DETECT_DEFECTS: "_stage_detect_defects",
        PipelineStage.GENERATE_DEFECT_REPORTS: "_stage_generate_defect_reports",
        PipelineStage.GENERATE_TEST_REPORTS: "_stage_generate_test_reports",
        PipelineStage.UPDATE_MEMORY: "_stage_update_memory",
    }

    def __init__(
        self,
        module_name: str,
        *,
        base_url: str | None = None,
        requirement: str | None = None,
    ) -> None:
        self.module = module_registry.get(module_name)
        self.ctx = ExecutionContext(
            module_name=module_name,
            base_url=base_url or settings.base_url,
        )
        self.requirement = requirement or f"Test the {module_name} module."
        self.stage_results: list[StageResult] = []

    # ── Public API ────────────────────────────────────────────────────────

    async def run(self, *, stages: list[PipelineStage] | None = None) -> ExecutionContext:
        """
        Execute the pipeline for this module.

        Args:
            stages: Subset of stages to run (defaults to full pipeline).

        Returns:
            The ExecutionContext with all accumulated data.
        """
        pipeline = stages or STANDARD_PIPELINE
        settings.ensure_dirs()

        console.print(Panel.fit(
            f"[bold cyan]MCP QA Pipeline[/bold cyan]\n"
            f"[dim]Module:[/dim] {self.ctx.module_name}\n"
            f"[dim]Run ID:[/dim] {self.ctx.run_id}\n"
            f"[dim]Target:[/dim] {self.ctx.base_url}",
            border_style="cyan",
        ))

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            for stage in pipeline:
                handler_name = self._STAGE_HANDLERS.get(stage)
                if not handler_name:
                    continue

                task = progress.add_task(
                    f"🔄 {stage.name.replace('_', ' ').title()}…", total=None
                )

                try:
                    handler = getattr(self, handler_name)
                    result = await handler()
                    self.stage_results.append(result)

                    if result.is_success():
                        self.ctx.mark_stage_complete(stage.name)
                        progress.update(
                            task,
                            description=f"✅ {stage.name.replace('_', ' ').title()}"
                        )
                    else:
                        self.ctx.mark_stage_error(stage.name, result.error or "Unknown")
                        progress.update(
                            task,
                            description=f"⚠️  {stage.name.replace('_', ' ').title()} — {result.status}"
                        )

                except Exception as exc:
                    err = f"{type(exc).__name__}: {exc}"
                    self.ctx.mark_stage_error(stage.name, err)
                    self.stage_results.append(StageResult(
                        stage, status="FAILED", error=err
                    ))
                    progress.update(
                        task,
                        description=f"❌ {stage.name.replace('_', ' ').title()} — FAILED"
                    )
                finally:
                    progress.remove_task(task)

        self._print_summary()
        return self.ctx

    # ── Stage Implementations ─────────────────────────────────────────────

    async def _stage_explore(self) -> StageResult:
        """Explore the application for this module."""
        from agent.explorer import explore_application

        try:
            data = await explore_application(
                base_url=self.ctx.base_url,
                module_name=self.ctx.module_name,
            )
            self.ctx.exploration_data = data
            return StageResult(PipelineStage.EXPLORE, data=data)
        except Exception as exc:
            # Continue with empty exploration data
            self.ctx.exploration_data = {
                "base_url": self.ctx.base_url,
                "pages": [],
                "nav_links": [],
            }
            return StageResult(
                PipelineStage.EXPLORE,
                status="FAILED",
                error=str(exc),
                data=self.ctx.exploration_data,
            )

    async def _stage_discover(self) -> StageResult:
        """Discover module-specific screens and elements."""
        pages = self.ctx.exploration_data.get("pages", [])
        nav_links = self.ctx.exploration_data.get("nav_links", [])
        self.ctx.discovered_pages = pages
        return StageResult(PipelineStage.DISCOVER, data={
            "page_count": len(pages),
            "nav_link_count": len(nav_links),
        })

    async def _stage_understand(self) -> StageResult:
        """Load module workflows and expected behaviors."""
        workflows = self.module.get_workflows()
        return StageResult(PipelineStage.UNDERSTAND, data={
            "workflow_count": len(workflows),
            "workflow_names": list(workflows.keys()),
        })

    async def _stage_load_documentation(self) -> StageResult:
        """Load documented expected behaviors."""
        from mcp.shared.doc_loader import load_module_docs

        docs = load_module_docs(self.ctx.module_name)
        self.ctx.module_documentation = docs
        return StageResult(PipelineStage.LOAD_DOCUMENTATION, data={
            "doc_count": len(docs.get("expected_behaviors", {})),
        })

    async def _stage_generate_tests(self) -> StageResult:
        """Generate or load test cases for this module."""
        from agent.planner import generate_test_plan
        from mcp.agents.memory_agent import load_memory

        memory = load_memory(self.ctx.module_name)
        self.ctx.memory_snapshot = memory

        test_plan = await generate_test_plan(
            requirement=self.requirement,
            exploration_data=self.ctx.exploration_data,
            module_memory=memory,
        )
        self.ctx.test_plan = test_plan
        scenario_count = len(test_plan.get("scenarios", []))
        return StageResult(PipelineStage.GENERATE_TESTS, data={
            "scenario_count": scenario_count,
        })

    async def _stage_execute_tests(self) -> StageResult:
        """Stage 6: Execute generated test scenarios and capture live state."""
        from agent.executor import execute_test_plan

        results = await execute_test_plan(
            test_plan=self.ctx.test_plan,
            base_url=self.ctx.base_url,
            execution_context=self.ctx,
        )
        self.ctx.test_results = results
        return StageResult(PipelineStage.EXECUTE_TESTS, data={
            "total_executed": len(results),
            "scenarios_executed": [r.get("id") for r in results],
        })

    async def _stage_validate_results(self) -> StageResult:
        """Stage 7: Independently validate executed scenario results against specs."""
        from mcp.agents.validation_agent import run_validation_agent

        val_summary = await run_validation_agent(self.ctx)
        return StageResult(PipelineStage.VALIDATE_RESULTS, data=val_summary)

    async def _stage_capture_evidence(self) -> StageResult:
        """Consolidate evidence references."""
        from mcp.shared.evidence_manager import consolidate_evidence

        evidence_summary = consolidate_evidence(self.ctx)
        return StageResult(PipelineStage.CAPTURE_EVIDENCE, data=evidence_summary)

    async def _stage_detect_defects(self) -> StageResult:
        """Detect and classify defects from failures."""
        from mcp.shared.defect_manager import detect_defects

        defects = await detect_defects(self.ctx)
        self.ctx.defects = defects
        return StageResult(PipelineStage.DETECT_DEFECTS, data={
            "defect_count": len(defects),
        })

    async def _stage_generate_defect_reports(self) -> StageResult:
        """Generate structured defect records."""
        from mcp.shared.defect_manager import save_defects

        saved = save_defects(self.ctx)
        return StageResult(PipelineStage.GENERATE_DEFECT_REPORTS, data={
            "saved_count": saved,
        })

    async def _stage_generate_test_reports(self) -> StageResult:
        """Generate the module-level QA report."""
        from mcp.shared.report_generator import generate_module_report

        report_path = generate_module_report(self.ctx)
        return StageResult(PipelineStage.GENERATE_TEST_REPORTS, data={
            "report_path": str(report_path),
        })

    async def _stage_update_memory(self) -> StageResult:
        """Persist learnings to module memory."""
        from mcp.agents.memory_agent import update_memory

        update_memory(self.ctx)
        return StageResult(PipelineStage.UPDATE_MEMORY, data={
            "module": self.ctx.module_name,
        })

    # ── Helpers ───────────────────────────────────────────────────────────

    def _print_summary(self) -> None:
        """Print a final summary panel."""
        ctx = self.ctx
        border = "green" if ctx.failed_count == 0 else "red"
        summary_text = (
            f"[bold]Pipeline Complete — {ctx.module_name.upper()}[/bold]\n"
            f"[green]Passed:[/green]   {ctx.passed_count}\n"
            f"[red]Failed:[/red]   {ctx.failed_count}\n"
            f"[yellow]Blocked:[/yellow]  {ctx.blocked_count}\n"
            f"[dim]Skipped:[/dim]  {ctx.skipped_count}\n"
            f"Defects:  {len(ctx.defects)}\n"
            f"Evidence: {len(ctx.evidence_paths)}\n"
            f"Memory:   Updated\n\n"
            f"[dim]Run ID: {ctx.run_id}[/dim]"
        )
        try:
            console.print()
            console.print(Panel.fit(summary_text, border_style=border, title="MCP QA Pipeline — Results"))
        except Exception:
            print(f"\n--- MCP QA Pipeline: {ctx.module_name.upper()} ---\nPassed: {ctx.passed_count}, Failed: {ctx.failed_count}, Defects: {len(ctx.defects)}")
