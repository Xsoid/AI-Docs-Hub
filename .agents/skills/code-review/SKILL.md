---
name: code-review
description: Perform an explicit diff-first semantic code review and record findings for the current AI Docs Hub patch fingerprint.
---

# Code Review

This is a semantic review pass, not deterministic verification and not security review.

1. Call prepare_patch_review with kind=code and the exact scope/base.
2. Run native Codex review explicitly with the matching scope, for example codex review --uncommitted or codex review --base BASE. Do not emulate slash commands through TUI automation.
3. Review changed files first and fetch only relevant contracts through project-scoped Docs MCP and blast-radius context through Codebase Memory.
4. Check task fit, correctness, regressions, compatibility, API/data/migration contracts, concurrency, resources, observability, tests, dead code, duplication, docs drift and project AGENTS rules.
5. Record code findings with severity, confidence, path/line, evidence, impact, remediation and violated rule. Do not report style preference alone.
6. Record passed only as no findings in reviewed scope. A changed fingerprint requires a fresh review.
