# RuleForge V10.2 — Observability / Pipeline Trace

This document defines the normative specification for pipeline observability.

## 1. Activation
Tracing is strictly opt-in.
- `engine.evaluate(source, context)` → `PipelineResult.Trace` is `null`.
- `engine.evaluate(source, context, trace=True)` → `PipelineResult.Trace` is populated.

## 2. Structure
`PipelineResult` contains:
- `Decisions`: List of `Decision` objects.
- `AppliedPatches`: List of all `AppliedPatch` objects across the pipeline.
- `FinalContext`: The mutated context.
- `Trace`: Optional list of `RuleTraceEntry`.

`RuleTraceEntry` contains:
- `RuleName` (string)
- `RuleIndex` (int)
- `Matched` (bool)
- `AppliedPatches` (List<string>): Paths of patches *actually applied* by this rule.
- `Actions` (List<string>): Action types produced (e.g., `["ALLOW"]`, `["SET"]`).

## 3. Rules
- The trace follows the exact sequential evaluation order.
- Unmatched rules are included with empty `Actions` and `AppliedPatches`.
- If a rule fails (runtime error), the pipeline halts and the trace contains the entry for the failed rule up to the point of failure.
- Does not trace AST internals or branch evaluation. Scope is strictly "What did the pipeline do?".
