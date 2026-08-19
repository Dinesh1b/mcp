# AI QA Agent --- Playwright QA Testing Skill

## Purpose

This skill defines a reusable AI-powered QA testing workflow for
Antigravity using:

-   Python
-   LLMs
-   Tools
-   MCP
-   Playwright
-   Pytest
-   Agent workflows
-   Browser automation
-   QA evidence and defect reporting

The goal is to build **Antigravity as an AI QA Agent** that can
understand a testing requirement, explore a web application, create a
test plan, execute tests through Playwright MCP, verify actual behavior,
identify defects, collect evidence, and produce a structured QA report.

------------------------------------------------------------------------

# 1. Core Architecture

Use the following architecture:

``` text
                    ┌───────────────────────┐
                    │      Antigravity      │
                    │       AI Agent        │
                    │         + LLM         │
                    └───────────┬───────────┘
                                │
                         Agent Workflow
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                 │
              ▼                 ▼                 ▼
           Python             Tools              MCP
        Orchestration       API / DB / FS      Tool Layer
              │                 │                 │
              └─────────────────┼─────────────────┘
                                │
                                ▼
                         Playwright MCP
                                │
                                ▼
                         Browser / Web App
                                │
                                ▼
                     Evidence + Verification
                                │
                                ▼
                           QA Report
```

## Responsibility Model

### LLM

Responsible for:

-   Understanding requirements
-   Reasoning about workflows
-   Creating test scenarios
-   Interpreting UI state
-   Comparing expected vs actual behavior
-   Identifying potential defects
-   Classifying defects
-   Producing human-readable reports

### Python

Responsible for:

-   Agent orchestration
-   Workflow control
-   Test execution coordination
-   Data processing
-   Retry logic
-   State management
-   Report generation
-   Deterministic utilities

### MCP

Responsible for exposing external capabilities to the agent.

Examples:

-   Browser automation
-   Filesystem
-   API
-   Database
-   GitHub
-   Other approved tools

### Playwright

Responsible for deterministic browser interaction:

-   Navigate
-   Click
-   Fill
-   Select
-   Inspect
-   Wait
-   Assert
-   Screenshot
-   Trace
-   Browser state

### Pytest

Responsible for deterministic automated assertions and test execution.

------------------------------------------------------------------------

# 2. Primary Objective

The agent must be capable of receiving a requirement such as:

``` text
Test the Inventory module.
```

and automatically perform:

``` text
Understand
   ↓
Explore
   ↓
Plan
   ↓
Execute
   ↓
Verify
   ↓
Reproduce failures
   ↓
Collect evidence
   ↓
Classify defects
   ↓
Generate QA report
```

The agent must not simply generate test cases.

It must actually execute and verify them whenever the required tools and
application access are available.

------------------------------------------------------------------------

# 3. QA Testing Philosophy

Follow these principles:

1.  Test behavior, not implementation.
2.  Never assume an action succeeded merely because the UI accepted the
    action.
3.  Verify the resulting application state.
4.  Use product documentation as the expected-behavior reference.
5.  Do not invent expected behavior.
6.  If requirements are ambiguous, record a gap instead of guessing.
7.  Reproduce failures before declaring a defect.
8.  Capture evidence for meaningful failures.
9.  Prefer stable selectors.
10. Avoid unnecessary fixed sleeps.
11. Keep deterministic assertions separate from LLM reasoning.
12. Do not modify production/application code simply to make tests pass.
13. Continue independent tests after an isolated failure.
14. Clearly distinguish application defects from test/environment
    failures.

------------------------------------------------------------------------

# 4. Module-Based QA Strategy

Organize testing by module.

Recommended modules:

1.  Login & Authentication
2.  Application Exploration & Navigation
3.  Functional Testing
4.  Form & Validation Testing
5.  CRUD Testing
6.  Inventory Testing
7.  Audit Testing
8.  Search / Filter / Sort / Pagination
9.  Import / Export
10. Error Handling
11. UI / UX
12. Permissions & Role-Based Access
13. API / Integration Testing
14. Regression Testing

Each module should have its own workflow where practical.

------------------------------------------------------------------------

# 5. Phase 1 --- Understand

When the user gives a QA requirement:

### Identify

-   Application
-   Environment
-   Module
-   Feature
-   User role
-   Preconditions
-   Test data
-   Expected behavior
-   Constraints

### Example

Input:

``` text
Test Item Import in Inventory.
```

Agent should identify:

``` text
Module: Inventory
Feature: Item Import
Testing type:
- Functional
- Validation
- Negative
- File upload
- Duplicate handling
- Error handling
```

If documentation exists, inspect it before determining expected
behavior.

------------------------------------------------------------------------

# 6. Phase 2 --- Application Exploration

Use Playwright MCP to explore the application.

### Explore

-   Login
-   Navigation
-   Menus
-   Submenus
-   Pages
-   Forms
-   Tables
-   Buttons
-   Modals
-   Dropdowns
-   Search
-   Filters
-   Pagination
-   Import/export
-   Notifications
-   Error messages

Do not assume the UI structure.

Inspect the actual application.

### Exploration Rules

Prefer:

``` text
getByRole
getByLabel
getByPlaceholder
getByText
getByTestId
```

Use CSS selectors when necessary.

Avoid fragile XPath unless no stable alternative exists.

------------------------------------------------------------------------

# 7. Phase 3 --- Generate Test Plan

For each feature generate:

## Functional Tests

Verify normal workflows.

## Validation Tests

Verify:

-   Required fields
-   Invalid formats
-   Minimum values
-   Maximum values
-   Invalid characters
-   Duplicate values
-   Empty values
-   Boundary values

## Negative Tests

Verify:

-   Invalid input
-   Unauthorized actions
-   Missing data
-   Invalid files
-   Incorrect workflow states
-   Network/API failures

## CRUD Tests

Verify:

-   Create
-   Read
-   Update
-   Delete

Also verify business rules around deletion.

## Search / Filter

Verify:

-   Exact search
-   Partial search
-   Case handling
-   Empty results
-   Multiple filters
-   Reset filters
-   Pagination
-   Sorting

## UI Tests

Verify:

-   Visibility
-   Alignment
-   Labels
-   Button states
-   Disabled states
-   Responsive behavior
-   Error messages
-   Toasts
-   Modals

------------------------------------------------------------------------

# 8. Phase 4 --- Test Execution

Execute tests through Playwright MCP.

For every action:

``` text
Locate element
    ↓
Perform action
    ↓
Wait for meaningful state change
    ↓
Inspect resulting state
    ↓
Assert expected behavior
```

Avoid:

``` python
time.sleep(5)
```

when a deterministic wait or assertion can be used.

Prefer waiting for:

-   Locator visibility
-   Locator state
-   URL change
-   Network completion
-   Response
-   DOM state
-   Expected notification
-   Table update

------------------------------------------------------------------------

# 9. Verification Rule

A successful UI action does NOT automatically mean the test passed.

Example:

``` text
Click Save
```

is only an action.

The agent must verify:

``` text
Record created
Correct values displayed
Success notification shown
Record persists after refresh
```

when those behaviors are expected.

------------------------------------------------------------------------

# 10. Failure Handling

When a test fails:

### Step 1

Capture the failure.

### Step 2

Determine whether it is:

-   Application defect
-   Test defect
-   Environment issue
-   Data issue
-   Authentication issue
-   Network/API issue
-   Timing issue

### Step 3

Reproduce independently.

### Step 4

Retry only when appropriate.

### Step 5

Capture evidence.

### Step 6

Classify severity.

### Step 7

Continue testing independent scenarios.

------------------------------------------------------------------------

# 11. Defect Severity

Use:

## Critical

System unusable, data corruption, security-critical failure, or major
business process completely blocked.

## High

Major business functionality broken with significant impact.

## Medium

Important functionality affected but workaround exists.

## Low

Minor UI, cosmetic, usability, or low-impact behavior issue.

Severity must be based on business impact, not merely how easy the bug
is to reproduce.

------------------------------------------------------------------------

# 12. Evidence Collection

For failures capture, when useful:

-   Screenshot
-   Playwright trace
-   Video
-   Console errors
-   Network errors
-   URL
-   Browser state
-   Relevant request/response
-   Test data
-   Reproduction steps

Recommended evidence structure:

``` text
evidence/
├── screenshots/
├── traces/
├── videos/
├── console/
└── network/
```

Use meaningful filenames:

``` text
TC_INV_004_item_import_duplicate.png
TC_AUD_012_delete_group.trace.zip
```

------------------------------------------------------------------------

# 13. MCP Tool Strategy

The agent should use MCP for tool access.

Recommended browser capabilities:

``` text
navigate
click
fill
select
hover
press
screenshot
inspect
evaluate
wait
browser tabs
console inspection
network inspection
```

Do not create fake tool results.

If a required tool is unavailable, clearly report the limitation.

------------------------------------------------------------------------

# 14. Agent Workflow

Implement the agent as modular stages:

``` text
Requirement
    ↓
Requirement Analyzer
    ↓
Application Explorer
    ↓
Test Planner
    ↓
Test Executor
    ↓
Verification Engine
    ↓
Failure Analyzer
    ↓
Defect Classifier
    ↓
Evidence Collector
    ↓
QA Reporter
```

Each stage should have a clear input and output.

------------------------------------------------------------------------

# 15. Suggested Python Project Structure

``` text
ai-qa-agent/
│
├── skill.md
│
├── agent/
│   ├── __init__.py
│   ├── planner.py
│   ├── explorer.py
│   ├── executor.py
│   ├── verifier.py
│   ├── failure_analyzer.py
│   ├── defect_classifier.py
│   └── reporter.py
│
├── mcp/
│   ├── __init__.py
│   └── playwright_client.py
│
├── workflows/
│   ├── __init__.py
│   ├── login.py
│   ├── navigation.py
│   ├── inventory.py
│   ├── audit.py
│   ├── crud.py
│   ├── search.py
│   └── import_export.py
│
├── tests/
│   ├── functional/
│   ├── validation/
│   ├── negative/
│   ├── crud/
│   ├── inventory/
│   ├── audit/
│   ├── search/
│   └── ui/
│
├── test-data/
│
├── evidence/
│   ├── screenshots/
│   ├── traces/
│   ├── videos/
│   ├── console/
│   └── network/
│
├── reports/
│
├── config/
│
├── prompts/
│
├── utils/
│
├── requirements.txt
├── pytest.ini
└── main.py
```

------------------------------------------------------------------------

# 16. Playwright Configuration

Use Playwright with:

-   Chromium
-   Firefox
-   WebKit
-   Headless mode
-   Headed mode
-   Screenshots on failure
-   Video on failure
-   Trace on retry
-   Configurable base URL
-   Configurable authentication
-   Environment-based configuration

Example configuration requirements:

``` text
baseURL
browser
headless
timeout
screenshot
video
trace
retries
workers
```

Do not hard-code secrets.

------------------------------------------------------------------------

# 17. Authentication

Authentication should be reusable.

Preferred approach:

``` text
Login once
   ↓
Create authenticated browser state
   ↓
Reuse storage state
   ↓
Run module tests
```

Credentials must come from environment variables or secure
configuration.

Never place real passwords or tokens in:

-   skill.md
-   source code
-   Git
-   test reports
-   screenshots
-   prompts

------------------------------------------------------------------------

# 18. LLM Tool-Calling Rules

The LLM should decide:

``` text
What should I do next?
```

The tool should execute:

``` text
How do I perform the action?
```

The LLM must not fabricate:

-   page state
-   test results
-   API responses
-   screenshots
-   DOM elements
-   defect evidence

Every factual execution result must come from a tool or test assertion.

------------------------------------------------------------------------

# 19. Deterministic vs AI Testing

Use AI for:

-   Exploration
-   Reasoning
-   Test generation
-   Workflow selection
-   Failure interpretation
-   Defect classification
-   Report summarization

Use deterministic automation for:

-   Clicking
-   Filling
-   Selecting
-   Assertions
-   API status checks
-   Data validation
-   Exact comparisons
-   Regression tests

This hybrid approach is preferred over making the LLM perform every
operation itself.

------------------------------------------------------------------------

# 20. QA Report

Generate a structured report.

Required columns:

  ------------------------------------------------------------------------------------------------------
  TC ID   Module   Scenario   Preconditions   Steps   Expected   Actual   Status   Severity   Evidence
                                                      Result     Result                       
  ------- -------- ---------- --------------- ------- ---------- -------- -------- ---------- ----------

  ------------------------------------------------------------------------------------------------------

Statuses:

``` text
PASS
FAIL
BLOCKED
SKIPPED
NOT APPLICABLE
```

The report must include:

``` text
Test Summary
----------------
Total Tests:
Passed:
Failed:
Blocked:
Skipped:

Defect Summary
----------------
Critical:
High:
Medium:
Low:
```

------------------------------------------------------------------------

# 21. Defect Report Format

For every confirmed defect:

``` text
Bug ID:
Module:
Title:
Severity:
Priority:

Precondition:

Steps to Reproduce:
1.
2.
3.
4.

Expected Result:

Actual Result:

Environment:

Browser:

Evidence:

Console Error:

Network Error:

Reproducibility:

Impact:

Suggested Investigation:
```

Do not invent a suggested fix if the root cause is unknown.

------------------------------------------------------------------------

# 22. Gap and Ambiguity Handling

If expected behavior is unclear:

``` text
Status: GAP / AMBIGUOUS
```

Record:

``` text
Requirement:
Observed behavior:
Missing clarification:
Potential interpretations:
Recommended clarification:
```

Do not convert an ambiguous requirement into a defect without sufficient
evidence.

------------------------------------------------------------------------

# 23. Regression Strategy

After fixing a confirmed defect:

1.  Re-run the original failing test.
2.  Verify the defect is fixed.
3.  Run related tests.
4.  Run the affected module regression suite.
5.  Run critical end-to-end workflows.

Record:

``` text
Original Result: FAIL
Retest Result: PASS
Regression Result: PASS
```

------------------------------------------------------------------------

# 24. Agent Commands

The agent should support commands such as:

``` text
Test the Inventory module.
```

``` text
Test Item Import.
```

``` text
Run regression testing.
```

``` text
Find bugs in Audit.
```

``` text
Test the complete application.
```

``` text
Retest failed cases.
```

``` text
Generate QA report.
```

``` text
Investigate this defect.
```

------------------------------------------------------------------------

# 25. Master Agent Prompt

Use the following as the primary system instruction for the QA agent:

> You are an AI QA Agent specialized in web application testing.
>
> Use Python for orchestration, LLM reasoning for planning and analysis,
> MCP for external tool access, and Playwright for browser automation.
>
> Your responsibility is to systematically explore applications, create
> appropriate test scenarios, execute tests, verify actual application
> state, detect defects, collect evidence, and produce accurate QA
> reports.
>
> Never claim a test passed without verification.
>
> Never invent tool results or application state.
>
> Use product documentation as the expected-behavior reference.
>
> When requirements are ambiguous, report a gap instead of guessing.
>
> When a failure occurs, reproduce it before classifying it as an
> application defect.
>
> Use deterministic Playwright assertions for exact verification.
>
> Use LLM reasoning for exploration, planning, interpretation, and
> defect analysis.
>
> Maintain evidence for important failures.
>
> Do not modify application code simply to make tests pass.
>
> Continue testing independent workflows after failures.
>
> At the end of every testing session, provide:
>
> 1.  Test summary
> 2.  Passed tests
> 3.  Failed tests
> 4.  Blocked tests
> 5.  Confirmed defects
> 6.  Severity classification
> 7.  Evidence
> 8.  Gaps and ambiguities
> 9.  Regression recommendations
>
> Your primary objective is reliable, reproducible, evidence-based QA.

------------------------------------------------------------------------

# 26. Definition of Done

The AI QA Agent is considered ready when it can:

-   Connect to a web application
-   Authenticate
-   Explore modules
-   Understand workflows
-   Generate test scenarios
-   Execute Playwright tests
-   Use MCP tools
-   Verify application state
-   Detect real defects
-   Reproduce failures
-   Capture screenshots
-   Capture traces
-   Collect errors
-   Classify severity
-   Generate QA reports
-   Retest defects
-   Run regression tests
-   Handle ambiguous requirements
-   Preserve reusable test workflows

The final system must be modular, reusable, deterministic where
verification matters, and capable of adding new application modules
without redesigning the entire agent.
Playwright Tester

Write Playwright test files, run them natively (zero AI tokens), and fix failures in an automated loop.

Why This Approach

There are three ways to do browser testing with AI:

AI drives the browser live — burns tokens on every click, every page load, every assertion

Screenshot-based (Claude-in-Chrome) — even worse, images are token-heavy and it's single-threaded

AI writes tests, Playwright runs them — tokens spent once on authoring, execution is free forever

This skill uses approach 3. The test files persist, grow over time into a regression suite, and run
in parallel via Playwright's native worker system. You get the AI's intelligence for test design
without paying for execution.

Prerequisites

Before first use, verify the project has Playwright installed. If not, install it:

npm install -D @playwright/test
npx playwright install chromium

Check for an existing playwright.config.ts. If missing, create a minimal one appropriate to the
project's framework (Next.js, Vite, static, etc.). Use webServer config to auto-start the dev
server when tests run.

Workflow

Phase 1: Assess

Read the project structure to understand the framework, entry points, and routing

Check for existing test files in tests/, e2e/, or __tests__/ directories

Identify what the user wants tested — if vague, read the codebase and suggest the highest-value targets (forms, auth flows, critical user paths)

Check for an existing playwright.config.ts and understand its setup

Phase 2: Author Tests

Write .spec.ts files organized by test strategy. Each file should be focused and independent.


Writing good tests:

Use Playwright's locator API — prefer getByRole(), getByLabel(), getByText() over CSS selectors, because they're resilient to markup changes and match how users actually find elements

Each test should be independent — no shared state between tests, use beforeEach for setup

Use descriptive test names that read like requirements: test('submits contact form with valid data and shows success message')

Add await expect() assertions that verify outcomes, not implementation details

For forms: test the complete flow (fill -> submit -> verify response), not just individual fields

Keep tests focused — one behavior per test, multiple assertions are fine if they verify the same behavior

When existing tests are found:

Read them first to understand coverage and patterns

Add new tests for uncovered areas rather than rewriting what exists

Update broken tests only if the breakage is due to intentional code changes

Match the existing style and conventions

Phase 3: Execute

Run the full test suite using Playwright's native runner:

npx playwright test --reporter=line 2>&1

Key flags to know:

--workers=auto — parallel execution across CPU cores (this is the default, no need to set it)

--reporter=line — clean, parseable output for reading results

--headed — only if the user specifically asks to watch the tests run

--project=chromium — single browser for speed during development; run all browsers before deploy

The test runner handles all parallelism natively. No sub-agents needed for execution.

Phase 4: Fix Loop

When tests fail, enter the fix loop (max 3 attempts):

Read the failure output — Playwright's error messages include the expected vs actual values, the selector that failed, and a snippet of the page state

Diagnose and categorize — Label each failure explicitly:

Test bug — wrong selector, timing issue, incorrect expected value

App bug — actual broken behavior in the application

This categorization matters because it determines what gets fixed (test file vs app code)

Fix the right thing:

Test bug → update the test file

App bug → fix the application code, explain what was broken

Timing issue → add appropriate waitFor or increase timeout on that specific action

Rerun and document — Always rerun after fixing and document the command used:

npx playwright test --reporter=line 2>&1

Report the rerun results even if all tests pass — the user needs to see confirmation.

If still failing after 3 attempts — stop, report what's failing and why, ask the user for guidance. Don't keep burning cycles on something that might need architectural input.

When reporting results, always include:

Total tests, passed, failed, skipped

For each failure: the test name, what was expected, what happened, and whether it's a test bug or app bug

The rerun command and its output

Suggested fix if you didn't auto-fix

Phase 5: Report

After all tests pass (or after the fix loop exhausts):

Summarize results in a clear table format

If any app bugs were found and fixed, list them explicitly

Suggest additional test coverage areas the user might want

Note any flaky tests that passed on retry (these need attention)

Swarm Mode

When the user wants comprehensive testing from multiple angles simultaneously, use sub-agents
to write tests in parallel, then run them all natively.

Example swarm configuration — spawn 3 sub-agents:

Agent 1: Happy Path — writes tests for core user journeys, success flows, standard inputs

Agent 2: Validation & Edge Cases — writes tests for error states, empty inputs, boundary values, special characters, XSS attempts

Agent 3: Accessibility & UX — writes tests for keyboard navigation, focus management, aria attributes, responsive behavior

Each agent writes its test files to the shared tests/e2e/ directory. Once all agents complete,
run the full suite once with npx playwright test. Playwright's worker system handles parallel
execution of the combined test files.

The key insight: sub-agents spend tokens on test design (the creative, high-value part), while
execution uses zero tokens regardless of how many tests were written.

To invoke swarm mode, tell Claude: "Use the playwright-tester skill in swarm mode" or "Run parallel
test agents" or "Test from multiple angles."

Tips

Start narrow, expand later. Test the specific thing the user changed first, then broaden coverage.

Don't over-test. A focused suite of 10-15 meaningful tests beats 100 trivial ones. Test behaviors users care about.

Use the config. If the project has a webServer config in playwright.config.ts, the dev server starts automatically — no need to start it manually.

Trace on failure. If a failure is confusing, rerun with --trace on to get a full trace file for debugging.

CI-ready. The test files this skill creates are standard Playwright tests — they run in CI pipelines with zero modification.