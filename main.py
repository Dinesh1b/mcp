"""
main.py — AI QA Agent CLI entry point.

Usage examples:
    python main.py test "Test the Inventory module."
    python main.py explore
    python main.py report
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

app = typer.Typer(
    name="ai-qa-agent",
    help="AI QA Agent — automated web application testing powered by LLM + Playwright.",
    add_completion=False,
)
console = Console()


@app.command()
def test(
    requirement: str = typer.Argument(
        ..., help='Testing requirement e.g. "Test the Inventory module."'
    ),
    url: str = typer.Option(None, "--url", "-u", help="Override base URL from .env"),
    headless: bool = typer.Option(None, "--headless/--headed", help="Run browser headless or headed"),
) -> None:
    """Run the full QA agent workflow: Explore → Plan → Execute → Report."""
    console.print(
        Panel.fit(
            f"[bold cyan]AI QA Agent[/bold cyan]\n[dim]{requirement}[/dim]",
            border_style="cyan",
        )
    )

    if url:
        import os
        os.environ["BASE_URL"] = url
    if headless is not None:
        import os
        os.environ["HEADLESS"] = "true" if headless else "false"

    asyncio.run(_run_full_workflow(requirement))


@app.command()
def explore(
    url: str = typer.Option(None, "--url", "-u", help="Override base URL from .env"),
) -> None:
    """Explore the application and print the UI snapshot."""
    if url:
        import os
        os.environ["BASE_URL"] = url
    asyncio.run(_run_explore())


@app.command()
def report() -> None:
    """List generated QA reports."""
    from config.settings import settings
    reports = list(settings.report_dir.glob("*.md"))
    if not reports:
        console.print("[yellow]No reports found.[/yellow]")
        return
    console.print(f"\n[bold]Found {len(reports)} report(s):[/bold]")
    for r in sorted(reports, reverse=True):
        console.print(f"  📄 {r}")


async def _run_full_workflow(requirement: str) -> None:
    from config.settings import settings
    from agent.explorer import explore_application
    from agent.planner import generate_test_plan
    from agent.executor import execute_test_plan
    from agent.defect_classifier import classify_defect
    from agent.reporter import generate_report

    settings.ensure_dirs()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:

        # Phase 1: Explore
        task = progress.add_task("🔍 Phase 1 — Exploring application…", total=None)
        try:
            exploration_data = await explore_application()
            progress.update(task, description="✅ Phase 1 — Exploration complete")
        except Exception as exc:
            console.print(f"[red]Exploration failed: {exc}[/red]")
            console.print("[yellow]Continuing with empty exploration data.[/yellow]")
            exploration_data = {"base_url": settings.base_url, "pages": [], "nav_links": []}
        progress.remove_task(task)

        # Phase 2: Plan
        task = progress.add_task("📋 Phase 2 — Generating test plan…", total=None)
        try:
            test_plan = await generate_test_plan(requirement, exploration_data)
            scenario_count = len(test_plan.get("scenarios", []))
            progress.update(task, description=f"✅ Phase 2 — {scenario_count} scenarios planned")
        except Exception as exc:
            console.print(f"[red]Test plan generation failed: {exc}[/red]")
            raise typer.Exit(1)
        finally:
            progress.remove_task(task)

        # Phase 3: Execute
        task = progress.add_task("🚀 Phase 3 — Executing tests…", total=None)
        try:
            results = await execute_test_plan(test_plan)
            progress.update(task, description="✅ Phase 3 — Test execution complete")
        except Exception as exc:
            console.print(f"[red]Test execution failed: {exc}[/red]")
            raise typer.Exit(1)
        finally:
            progress.remove_task(task)

        # Phase 4: Classify defects
        task = progress.add_task("🔬 Phase 4 — Classifying defects…", total=None)
        for result in results:
            if result["status"] == "FAIL" and result.get("failure_analysis"):
                fa = result["failure_analysis"]
                if fa.get("failure_type") == "application_defect":
                    try:
                        dc = await classify_defect(
                            scenario={"id": result["id"], "title": result["title"]},
                            failure_analysis=fa,
                        )
                        result["defect_classification"] = dc
                    except Exception:
                        pass
        progress.remove_task(task)

        # Phase 5: Report
        task = progress.add_task("📊 Phase 5 — Generating QA report…", total=None)
        try:
            report_path = generate_report(requirement, test_plan, results)
            progress.update(task, description="✅ Phase 5 — Report generated")
        except Exception as exc:
            console.print(f"[red]Report generation failed: {exc}[/red]")
            raise typer.Exit(1)
        finally:
            progress.remove_task(task)

    # Summary
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    blocked = sum(1 for r in results if r["status"] == "BLOCKED")
    skipped = sum(1 for r in results if r["status"] == "SKIPPED")

    console.print()
    console.print(
        Panel.fit(
            f"[bold]Test Summary[/bold]\n"
            f"✅ Passed:  {passed}\n"
            f"❌ Failed:  {failed}\n"
            f"🚫 Blocked: {blocked}\n"
            f"⏭️  Skipped: {skipped}\n\n"
            f"📄 Report: [cyan]{report_path}[/cyan]",
            border_style="green" if failed == 0 else "red",
            title="AI QA Agent — Results",
        )
    )


async def _run_explore() -> None:
    from config.settings import settings
    from agent.explorer import explore_application
    import json

    settings.ensure_dirs()
    console.print("[cyan]Exploring application…[/cyan]")
    try:
        data = await explore_application()
        console.print(json.dumps(data, indent=2, default=str))
    except Exception as exc:
        console.print(f"[red]Exploration failed: {exc}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
