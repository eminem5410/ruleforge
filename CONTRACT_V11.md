# RuleForge V11.0 — Adapter / Effect Integration Contract

This document defines the normative specification for integrating RuleForge with external systems (FHIR, ERP, DBs, APIs).

## 1. Golden Rule (Architectural Boundary)
RuleForge produces **declarative effects**; the Host decides if, how, when, and transactionally where to materialize them.
A successful `PipelineResult` does NOT guarantee that SQL/FHIR/Kafka/HTTP was executed successfully. That is the exclusive responsibility of the Host.

## 2. Architecture
```text
External System
      │
      ▼
Input Adapter (Host)
      │
      ▼
Context + Schema
      │
      ▼
┌──────────────────────┐
│     RuleForge Core   │
│ Lexer / Parser       │
│ Semantic / Evaluator │
│ Compiler / Engine    │
└──────────────────────┘
      │
      ▼
  PipelineResult
      │
      ├── Decisions
      ├── AppliedPatches
      ├── FinalContext
      └── Trace?
      │
      ▼
 Effect Adapter (Host)
      │
      ├── SET → state mutation
      └── EMIT → intent handling
      │
      ▼
External System
3. Effect Materialization (Host Responsibility)
AppliedPatches[]: Represent state mutations (SET). The Host translates this to SQL UPDATE, REST PUT/PATCH, or FHIR transactions.
Actions (EMIT): Represent declared intents. The Host routes this to Event Handlers, Message Brokers, or Webhooks.
4. Repository Structure
Adapters are considered reference integrations, not dependencies of the Core.
ruleforge/
├── core/               (The pure, domain-independent engine)
├── engine/             (Orchestration layer)
├── conformance/        (Canonical test vectors)
└── adapters/           (Reference integrations - FHIR, ERP, etc.)
RuleForge.Core MUST NOT contain references to FHIR, ERP, SQL, HTTP, or specific external systems.
