# RuleForge Adapter Specification

This document defines the architectural contract for RuleForge Adapters (V2.0.0).
Adapters are responsible for bridging domain-specific data (FHIR, ERP) and the domain-agnostic RuleForge Core.

## 1. Core Philosophy
RuleForge Core knows NOTHING about FHIR, ERP, Patients, or Invoices.
Adapters know the domain and translate it to a generic RuleForge Context.

## 2. Pipeline Architecture
Domain Object (e.g., FHIR Resource)
      ↓
Domain Adapter (e.g., FhirAdapter.to_context())
      ↓
RuleForge Context (JSON)
      ↓
RuleForgeEngine.evaluate(rule, context)
      ↓
Decision (JSON)
      ↓
Domain Adapter / Host Application (e.g., Vantari mapping Decision to FHIR Actions)

## 3. Golden Rule of Adapters
Adapters DO NOT execute side effects.
RuleForge returns a Decision (e.g., `APPLY "AUTO_APPROVE"`).
The host application (Vantari/ContaFlow) decides what `AUTO_APPROVE` actually does in the database or API.

## 4. The Golden Architectural Rule
An adapter may translate domain data into a RuleForge-compatible context, but the RuleForge Core must remain unaware of the domain that produced that context.

This ensures that RuleForge remains a pure, domain-agnostic decision engine, allowing it to be reused across Vantari (HealthTech), ContaFlow (ERP), or any future system without modifying the core.
