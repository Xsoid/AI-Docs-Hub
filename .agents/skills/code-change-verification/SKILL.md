---
name: code-change-verification
description: Run AI Docs Hub deterministic verification for the current project patch before semantic review.
---

# Code Change Verification

Use the project-scoped AI Docs Hub MCP or CLI. Do not invent a second project test matrix and do not start an LLM review from this skill.

1. Select the exact scope: working, staged, range, or branch. Pass base for range/branch.
2. Run verify_patch or scripts/verify-patch. It discovers existing project entrypoints and always runs git diff check and secret scan.
3. Treat failed, errored, required-command, or secret results as a hard block. A missing optional tool is skipped/not_available, never passed.
4. Continue to code and security review only when the verification result is passed.
5. If any relevant byte changes, discard old results and repeat the complete flow for the new fingerprint.

Reports remain in ignored Hub storage and must contain metadata/digests, not source snippets, full diff, secrets, or absolute project paths.
