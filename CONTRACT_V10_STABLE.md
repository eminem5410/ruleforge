# RuleForge V10.0 — Context Pipeline Contract (Stable)

This document defines the normative specification for the V10.0 stable release.
It introduces the `RuleEngine` (Pipeline) layer that orchestrates rule execution and context mutation, strictly preserving the purity of the V7-V9 evaluation core.

## 1. Golden Rule (Architecture)
**Core declares. Engine orchestrates. Host applies. Adapter materializes.**
The Core (Lexer/Parser/Evaluator/Compiler) remains a pure deterministic function. The Engine orchestrates sequential execution and context mutation.

## 2. Pipeline Mechanics
1. **Cloning:** The Engine receives an `OriginalContext` and creates a `WorkingContext` (deep copy). The original remains immutable.
2. **Sequential Evaluation:** Rules are evaluated strictly in declaration order.
3. **Visibility (Rule N+1):** Rule N+1 sees the `WorkingContext` modified by Rule N.
4. **Last-Write-Wins (LWW):** If multiple rules patch the same path, the last one persists.

## 3. Atomicity of Application
Patches are calculated during evaluation. They are applied to the `WorkingContext` **only if** the entire rule evaluation succeeds without runtime errors (`RF4001`/`RF4002`).
If a patch expression fails, the rule fails, NO patches for that rule are applied, and the pipeline halts, returning the error.

## 4. Unmatched Rules
If a rule does not match (`matched = false`), it produces no patches and no actions. The pipeline continues to the next rule.

## 5. Audit Trail (PipelineResult)
The Engine returns a `PipelineResult` containing:
- `Decisions[]`: The decision for each rule.
- `AppliedPatches[]`: History of applied patches.
- `FinalContext`: The state of the context after all patches.
- `OriginalContext`: The untouched original context.

Each `AppliedPatch` contains:
- `RuleName`, `RuleIndex`, `PatchIndex`
- `Path`, `OldValue`, `NewValue`
