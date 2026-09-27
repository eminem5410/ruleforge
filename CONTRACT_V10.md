# RuleForge V10.0 — Context Mutation & Patching Contract

This document is the normative specification for the V10.0 extension. 
It introduces context mutation, but strictly preserves the pure functional nature of the V7-V9 evaluation core.

## 1. Objective
Allow rules to declare intentions to mutate the context via `SET`, deterministically and auditable, without side-effects in the core engine.

## 2. Syntax
```text
<action> ::= ... | SET <context_path> = <expression>
3. Declarative Model (Intents, not Side-Effects)
SET does NOT modify the context in memory during evaluation.
The engine returns a list of Patches in the Decision. The host applies the patches between evaluations if desired.
The action is resolved as:
{ "action_type": "SET", "value": "customer.status", "payload": "blocked" }

4. Typing
The <context_path> must exist in the schema (RF3002).
The type of <expression> must match the schema type of the path (RF3001).
5. Atomicity
If a runtime error occurs evaluating the <expression>, the rule fails (RF4001/RF4002) and no patches are emitted.
