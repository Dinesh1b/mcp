---
name: playwright-tester
description: Write Playwright test files, run them natively (zero AI tokens), and fix failures in an automated loop.
---

# Playwright Tester Skill

Write Playwright test files, run them natively (zero AI tokens), and fix failures in an automated loop.

## Why This Approach

There are three ways to do browser testing with AI:
1. **AI drives the browser live** — burns tokens on every click, every page load, every assertion.
2. **Screenshot-based** — images are token-heavy and single-threaded.
3. **AI writes tests, Playwright runs them** — tokens spent once on authoring, execution is free forever.

This skill uses approach 3. Test files persist, grow over time into a regression suite, and run in parallel via Playwright's native worker system.

## Workflow

### Phase 1: Assess
- Read project structure to understand the framework, entry points, and routing.
- Check for existing test files in `tests/`, `e2e/`, or `__tests__/`.
- Check for an existing `playwright.config.ts` or configuration.

### Phase 2: Author Tests
- Write focused, independent `.spec.ts` or `.py` Playwright test files.
- Prefer resilient locators (`getByRole()`, `getByLabel()`, `getByText()`).
- Keep tests independent with proper setup (`beforeEach`).
- Add assertions (`expect()`) that verify outcomes, not implementation details.

### Phase 3: Execute
- Run the suite using Playwright's native runner:
  ```bash
  npx playwright test --reporter=line 2>&1
  ```
  *(Or `python -m pytest` for Python Playwright suites)*.

### Phase 4: Fix Loop
- **Diagnose and categorize**:
  - **Test bug** — wrong selector, timing issue, incorrect expectation (update test file).
  - **App bug** — actual broken behavior in application (fix app code & explain).
  - **Timing issue** — add appropriate wait or increase action timeout.
- Rerun and document results (max 3 attempts).

### Phase 5: Report
- Summarize results in a clean table format:
  - Total tests, passed, failed, skipped.
  - Failure categorization and root cause.
  - Final release recommendations.

## Swarm Mode
When comprehensive multi-angle testing is needed, spawn parallel agents to author test suites simultaneously:
- **Agent 1: Happy Path** — core user journeys & success flows.
- **Agent 2: Validation & Edge Cases** — error states, empty inputs, boundaries, special characters.
- **Agent 3: Accessibility & UX** — keyboard navigation, focus management, aria attributes.

Run all tests natively with `npx playwright test` after authoring completes.
