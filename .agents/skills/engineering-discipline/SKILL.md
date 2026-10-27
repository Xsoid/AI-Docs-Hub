---
name: engineering-discipline
description: Apply to every code change in any project. Design the data first, prove behavior with tests, keep changes small, and remove complexity.
---

# Engineering Discipline

Use this skill when you write or change code. The project's own `AGENTS.md` and its workflow skills take precedence where they conflict. The ideas are inspired by https://github.com/unclebob/ub-mode; this text is an independent formulation.

Work in three passes, in this order: get it working, make it clean, then close it out.

## 1. Get It Working

### Scope

- Find the smallest change that solves the stated problem. Do not add work that nobody asked for.
- Before you add code, look for code, branches, or options that you can remove instead.
- Each rule, constant, or decision has exactly one owner in the code. Change it there.
- Define the result that proves the task is done before you start, and work toward that check.

### Design

- Decide the data structures first. Write the logic after the shape is correct.
- Choose types and structures that cannot hold an invalid state.
- Validate and parse external input once, at the boundary. Code inside the boundary trusts the parsed value.
- Keep business rules in pure functions. Put I/O, time, and randomness at the edges.
- Do not suppress compiler, type-checker, or linter errors to make code pass.
- An operation that runs twice, or restarts after a partial failure, must leave the same final state.
- Do not share mutable state between independent parts. If sharing is necessary, allow one writer and make the structure enforce it.
- When a new requirement does not fit the current design, design as if the requirement existed from day one. Deliver that design in small steps instead of adding a special case.
- Keep a short glossary of domain terms when the domain has its own vocabulary. Do not restructure code that is already clear and local.

### Tests First

- Write a test that fails before you change the behavior.
- Run it and confirm that it fails for the expected reason.
- Write the minimum code that makes it pass.
- If you cannot write a meaningful test, say so. Do not write a test that only exercises the implementation.

### When Fixes Keep Failing

- If two attempts based on the same assumption fail the same check, stop.
- Write that assumption as one sentence and test whether it is true.
- Fix or drop the wrong assumption before you try a third fix.

### Tools Over Repetition

- If a task repeats over many units and is error-prone by hand, do one unit manually, then write a script that reproduces that result for the rest.

## 2. Make It Clean

### Root Causes

- Reproduce the defect first.
- Fix the cause. A check that only hides the symptom is not a fix.

### Small Verified Steps

- Split the work into units that you can check one at a time. Finish and verify a unit before you start the next one.

### Test Quality

- Tests call the public interface the way a real caller does and assert on the visible result.
- Delete a test that would still pass if the code under test returned nothing.

### Refactoring

- Pin the current behavior with tests.
- Change the structure.
- Run the same tests to prove that the behavior did not change.

### Quality Gates

Use these gates when the project provides the tools. If a tool is not available, report the gate as skipped, never as passed.

- Complexity: keep each function's CRAP score below 10 (for example with `crapper`). Split the function, add tests, or both. Decide case by case whether a flat `switch`/`match` is worth splitting.
- Duplication: remove structural duplicates with similarity 0.8 or higher (for example with `dryer`).
- Mutation testing: cover uncovered code, kill surviving mutants, and delete dead code (for example with `mutator`).

## 3. Close It Out

- Keep a running log of each action and its reason. Give the user that log at the end.
- Keep the main conversation small. Send large searches and bulk output to subagents or files, and keep only the summary.
- Before you remove worktrees, branches, or caches, confirm that nothing still uses them. Leave uncommitted work in place until the user decides.
- Commit and push only when the user asks. Make each commit small and ordered, and state why, what changed, and how you verified it.
