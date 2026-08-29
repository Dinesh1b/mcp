"""
main.py — AI QA Agent CLI entry point.

Usage examples:
    python main.py test "Test the Inventory module."
    python main.py explore
    python main.py report
"""

from __future__ import annotations

import argparse
import asyncio
import os
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


async def run_test_workflow(requirement: str) -> None:
    from agent.explorer import explore_application
    from agent.planner import generate_test_plan
    from agent.executor import execute_test_plan
    from agent.defect_classifier import classify_defect
    from agent.reporter import generate_report
    from agent.repro_engine import ReproductionEngine

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

    # Step 5: Report
    print("\n📊 [5/5] Generating QA Markdown and JSON reports...")
    try:
        report_path = generate_report(requirement, test_plan, results)
        print(f"✅ QA Report successfully saved:\n   {report_path}")
    except Exception as exc:
        print(f"❌ Report generation failed: {exc}")
        return

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
    reports = list(settings.report_dir.glob("*.md"))
    if not reports:
        print("\n[!] No reports found in reports/ directory.\n")
        return
    print(f"\nFound {len(reports)} QA Report(s):")
    for r in sorted(reports, reverse=True):
        print(f"  📄 {r}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Stockount AI QA Platform (Antigravity + Gemini + MCP + Playwright)",
        epilog="Principle: 'Docs are reference; the live app is what we actually test.'",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: test
    test_parser = subparsers.add_parser("test", help="Run full QA workflow on a requirement")
    test_parser.add_argument("requirement", type=str, help="Testing requirement string")
    test_parser.add_argument("--url", "-u", type=str, default=None, help="Base URL override")
    test_parser.add_argument("--headless", action="store_true", default=None, help="Run headless")
    test_parser.add_argument("--headed", action="store_true", default=None, help="Run headed")

    # Command: crawl-docs
    subparsers.add_parser("crawl-docs", help="Crawl and structure docs.stockount.com")

    # Command: explore
    explore_parser = subparsers.add_parser("explore", help="Explore live application and map elements")
    explore_parser.add_argument("--module", "-m", type=str, default=None, help="Target module name")
    explore_parser.add_argument("--url", "-u", type=str, default=None, help="Base URL override")

    # Command: reproduce
    repro_parser = subparsers.add_parser("reproduce", help="Reproduce bug or execute step sequence")
    repro_parser.add_argument("target", type=str, help="Sequence, bug repro text, or test case file path")
    repro_parser.add_argument("--url", "-u", type=str, default=None, help="Base URL override")

    # Command: report
    subparsers.add_parser("report", help="List generated QA reports")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if hasattr(args, "url") and args.url:
        os.environ["BASE_URL"] = args.url
    if hasattr(args, "headless") and args.headless is not None:
        if args.headless:
            os.environ["HEADLESS"] = "true"
    if hasattr(args, "headed") and args.headed:
        os.environ["HEADLESS"] = "false"

    # Reload settings after env overrides
    settings.reload()

    if args.command == "test":
        asyncio.run(run_test_workflow(args.requirement))
    elif args.command == "crawl-docs":
        asyncio.run(run_crawl_docs())
    elif args.command == "explore":
        asyncio.run(run_explore(args.module))
    elif args.command == "reproduce":
        asyncio.run(run_reproduce(args.target))
    elif args.command == "report":
        list_reports()


if __name__ == "__main__":
    main()
