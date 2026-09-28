---
name: security-review
description: Perform a separate adaptive threat-informed security review and record it for the current AI Docs Hub patch fingerprint.
---

# Security Review

This pass is independent from code review and must never be represented by a code-review result.

1. Call prepare_patch_review with kind=security and the exact scope/base.
2. Use the returned changed-file security surface as a delta threat model. Docs-only changes receive a low-risk scope; auth, permissions, public HTTP, input handling, database, filesystem, subprocess, secrets, sessions, dependencies, CI/CD, deployment, logging or tenant isolation changes receive deeper review.
3. Use existing project security commands only when already available and accepted by the project. Never install a scanner silently; missing tooling is not_available.
4. Check only relevant classes such as auth bypass, injection, XSS/CSRF, SSRF, path traversal, command execution, unsafe deserialization, secret leakage, insecure defaults, privilege escalation, supply-chain regression and sensitive logging.
5. Record each finding with severity (critical/high/medium/low/info), confidence, prerequisite, asset/boundary, evidence, path/line, remediation and validation.
6. Record a positive result only as no findings in reviewed scope. Never claim absolute project security. Repeat after any fingerprint change.
