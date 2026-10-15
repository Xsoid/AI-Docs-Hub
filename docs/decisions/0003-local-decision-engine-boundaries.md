# 0003: Keep Local Decisions Typed, Offline And Non-Authoritative

Date: 2026-10-15

Status: Accepted

## Context

Hub already has canonical patch fingerprints, lifecycle surface metadata, Context Manifest and Skill Intelligence scores. A generic prompt or model platform would duplicate those contracts and could accidentally influence mandatory gates.

## Decision

Hub uses one typed registry for bounded boolean, choice and score decisions. The default provider is deterministic offline rules in shadow mode. Rules return controlled reason codes and mark heuristic scores as uncalibrated. A result is advice only. It cannot alter Project Lifecycle, security depth minimum, confirmation, project scope or writes.

The optional local adapter is not a dependency. It accepts a bounded request only through an explicitly configured proxy-free loopback HTTP endpoint. It rejects non-loopback endpoints and redirects, validates the response and fails closed. Hub does not install a model, download weights or call an external service.

No model implementation is selected for this release. The repository has no bundled or configured Jev-compatible implementation to verify. Its license, Apple Silicon/Linux support and resource footprint are therefore unknown and it is not a supported backend. The generic loopback contract is intentionally the only adapter surface until a separately reviewed local implementation supplies those facts.

Project-specific engine settings are not added to Project Config v1. The shipped policy is global, fixed and non-authoritative. A future override requires a separate schema and policy decision.

## Consequences

The implementation reuses existing Lifecycle, Context Manifest and Skill Intelligence primitives. Cached decision metadata and metrics are local ignored artifacts under `storage/decision-engine/<project>/`. A future promotion from shadow to advisory or auto requires evidence from synthetic and local observations, calibrated confidence where relevant, an explicit policy decision and a new review. This release enables no auto decision.
