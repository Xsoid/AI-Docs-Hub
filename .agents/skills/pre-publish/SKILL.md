---
name: pre-publish
description: Check AI Docs Hub publishability for the exact current patch before commit, push, or pull request.
---

# Pre-Publish

Use get_pre_publish_status or scripts/pre-publish for the exact scope. PUBLISHABLE requires passed deterministic verification, a current passed code review, and a current passed separate security review without hard-block findings. Missing, incomplete, failed, or stale results block publication. NO_PATCH means the selected scope is clean; it is not a reviewed patch.

Never commit or push as part of this skill. A fix changes the fingerprint and requires verification and both reviews again.
