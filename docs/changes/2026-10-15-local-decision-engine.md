# Local Decision Engine

Date: 2026-10-15

Hub now includes a typed offline Decision Engine for bounded lifecycle, context and Skill Intelligence metadata. The default rules provider runs in shadow mode. It cannot change gates, confirmations, writes or connected projects.

The change adds local project-scoped cache and metrics, a loopback-only optional adapter contract, synthetic benchmark and read-only MCP status tool. See [ADR 0003](../decisions/0003-local-decision-engine-boundaries.md) for the boundary and promotion policy.
