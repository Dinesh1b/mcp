"""
main.py — Stockount AI QA Platform CLI Entry Point.

Ground Principle: "Docs are reference; the live app is what we actually test."

Usage:
    python main.py test "Test the Audit Plan creation flow"
    python main.py test "Explore the Sales module"
    python main.py crawl-docs
    python main.py reproduce "Create Audit Plan -> Perform Audit -> Verify Audit History"
    python main.py explore --module inventory
    python main.py report
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

from config.settings import settings

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def print_banner(title: str, subtitle: str = "") -> None:
    border = "=" * 70
    print(f"\n{border}")
    print(f"  {title}")
    if subtitle:
        print(f"  {subtitle}")
    print(f"  Core Principle: 'Docs are reference; the live app is what we actually test.'")
    print(f"{border}\n")


async def run_crawl_docs() -> None:
    from knowledge.doc_crawler import DocCrawler
    print_banner("CRAWLING STOCKOUNT DOCUMENTATION", "https://docs.stockount.com")
    crawler = DocCrawler()
    res = await crawler.crawl()
    print(f"✅ Successfully crawled and structured {res['crawled_count']} pages.")
    print(f"📁 Cache saved to: {res['cache_file']}\n")


async def run_explore(module: Optional[str] = None) -> None:
    from agent.explorer import explore_application
    import json

    settings.ensure_dirs()
    print_banner("EXPLORING LIVE APPLICATION", f"Target: {module or 'All Modules'}")
    try:
        data = await explore_application(target_module=module)
        print(json.dumps(data, indent=2, default=str))
    except Exception as exc:
        print(f"❌ Exploration failed: {exc}")


async def run_reproduce(target: str) -> None:
    from agent.repro_engine import ReproductionEngine
    from agent.executor import execute_test_plan
    from agent.reporter import generate_report

    settings.ensure_dirs()
    print_banner("REPRODUCTION ENGINE", f"Target: {target}")
    engine = ReproductionEngine()
    test_plan = engine.parse_input(target, file_path=target if Path(target).exists() else None)
    print(f"📋 Normalized {len(test_plan.get('scenarios', []))} test scenario(s). Module: {test_plan.get('module')} [{test_plan.get('doc_status')}]")
    print("🚀 Executing...")

    results = await execute_test_plan(test_plan)
    report_path = generate_report(target, test_plan, results)
    print(f"\n✅ Reproduction run complete! QA Report generated at:\n   {report_path}\n")


async def run_test_workflow(requirement: str) -> None:
    from agent.explorer import explore_application
    from agent.planner import generate_test_plan
    from agent.executor import execute_test_plan
    from agent.defect_classifier import classify_defect
    from agent.reporter import generate_report
    from agent.repro_engine import ReproductionEngine

    settings.ensure_dirs()
    print_banner("STOCKOUNT AI QA RUNNER", f"Requirement: {requirement}")

    # Step 1: Inspect Live App & Coverage
    print("🔍 [1/5] Inspecting live application & doc coverage map...")
    inferred_mod = ReproductionEngine._infer_module(requirement)
    try:
        exploration_data = await explore_application(target_module=inferred_mod)
        print(f"   Discovered {len(exploration_data.get('modules_discovered', []))} module section(s).")
    except Exception as exc:
        print(f"   Exploration notice: {exc}. Continuing with baseline state.")
        exploration_data = {"base_url": settings.base_url, "pages": []}

    # Step 2: Plan
    print("\n📋 [2/5] Generating reference-grounded test plan...")
    try:
        test_plan = await generate_test_plan(requirement, exploration_data)
        scenarios = test_plan.get("scenarios", [])
        print(f"   Planned {len(scenarios)} scenario(s) | Doc Coverage: `{test_plan.get('doc_status')}`")
    except Exception as exc:
        print(f"❌ Planning failed: {exc}")
        return

    # Step 3: Execute & Validate
    print("\n🚀 [3/5] Executing browser workflows & multi-level validation...")
    try:
        results = await execute_test_plan(test_plan)
        print(f"   Executed {len(results)} step(s) / scenario(s).")
    except Exception as exc:
        print(f"❌ Execution failed: {exc}")
        return

    # Step 4: Classify Defects & Discrepancies
    print("\n🔬 [4/5] Analyzing discrepancies and classifying defects...")
    for result in results:
        if result.get("status") == "FAIL" and result.get("failure_analysis"):
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

    # Step 5: Report
    print("\n📊 [5/5] Generating QA Markdown and JSON reports...")
    try:
        report_path = generate_report(requirement, test_plan, results)
        print(f"✅ QA Report successfully saved:\n   {report_path}")
    except Exception as exc:
        print(f"❌ Report generation failed: {exc}")
        return

    # Summary Output
    passed = sum(1 for r in results if r.get("status") == "PASS")
    failed = sum(1 for r in results if r.get("status") == "FAIL")
    observed = sum(1 for r in results if r.get("status") == "OBSERVED")
    unverifiable = sum(1 for r in results if r.get("status") == "UNVERIFIABLE")
    disc = sum(1 for r in results if r.get("status") == "DISCREPANCY")

    print("\n" + "=" * 50)
    print(f"  Summary: {test_plan.get('module')} [{test_plan.get('doc_status')}]")
    print(f"  ✅ Validated (PASS):       {passed}")
    print(f"  ❌ Failed (FAIL):          {failed}")
    print(f"  🔍 Exploratory (OBSERVED): {observed}")
    print(f"  ❓ Unverifiable:          {unverifiable}")
    print(f"  ⚠️ Doc Discrepancies:     {disc}")
    print("=" * 50 + "\n")


def list_reports() -> None:
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
