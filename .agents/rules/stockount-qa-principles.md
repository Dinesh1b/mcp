---
trigger: manual
---

# Stockount QA Core Principles

## Core Principle: "Docs are reference; the live app is what we actually test."

### Documentation as Reference
Use the Stockount documentation as a reference source for understanding modules, terminology, workflows, business rules, and expected behavior where available. Do not assume the documentation is complete or always authoritative. Always inspect the live application through MCP + Playwright and compare the observed behavior with the available documentation. When documentation and the live application differ, record the discrepancy as a finding instead of guessing or silently overriding either source.

### Validation Wording & Rules
- **Documented areas**: Validate actual behavior against documented expectations where applicable.
- **Undocumented areas**: Explore the live application, capture UI/API behavior, and report findings as `OBSERVED` / `UNVERIFIABLE`; never fabricate expected results.

### Discrepancy Handling
- If the live application displays elements, flows, or API responses that differ from the docs, capture evidence (screenshot, DOM, network response) and log a **Documentation Discrepancy** finding.
- Do not fabricate expected outcomes for undocumented modules (e.g. Sales, Purchases, Reports) — observe and document them accurately.
