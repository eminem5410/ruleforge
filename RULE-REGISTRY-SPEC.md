# RuleForge Rule Registry Specification (V4.0.0)

This document defines the contract for managing and persisting rules.
The Rule Registry allows rules to be stored, versioned, and retrieved by ID, moving RuleForge from a stateless API to a stateful managed service.
The Core Engine remains completely unaware of the storage mechanism (PostgreSQL, Memory, etc.).

## 1. Rule Object Model
A registered rule contains the following metadata:
- `rule_id` (string): Unique identifier for the rule (e.g., "adult_check").
- `version` (int): Auto-incremented version number for this rule_id.
- `language_version` (int): The RuleForge language version this rule was written for.
- `source` (string): The RuleForge source code.
- `status` (enum): The lifecycle state of the rule. Allowed: "DRAFT", "ACTIVE", "ARCHIVED".
- `created_at` (datetime): Timestamp of creation.
- `updated_at` (datetime): Timestamp of last update.

## 2. Determinism Guarantee
Fetching a rule by `rule_id` and `version` MUST always return the exact same `source` and `language_version`.
This ensures that historical decisions can be perfectly reproduced.

## 3. Rule Repository Protocol
The API will use a repository pattern to abstract storage.

class RuleRepository(Protocol):
    def get_rule(self, rule_id: str, version: int = None) -> Rule: ...
    def save_rule(self, rule_id: str, source: str, language_version: int) -> Rule: ...
    def list_rules(self, status: str = None) -> List[Rule]: ...
    def delete_rule(self, rule_id: str) -> None: ...

Initially, this will be implemented as an InMemoryRuleRepository. Later as a PostgresRuleRepository.

## 4. REST API Endpoints
- POST /v1/rules: Create a new rule (returns version 1).
- GET /v1/rules/{rule_id}: Get the ACTIVE version of a rule.
- GET /v1/rules/{rule_id}/versions/{version}: Get a specific historical version.
- POST /v1/rules/{rule_id}/evaluate: Evaluate the ACTIVE version against a provided context.
