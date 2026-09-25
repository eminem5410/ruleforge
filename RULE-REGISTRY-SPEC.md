# RuleForge Rule Registry Specification (V4.1.0)

This document defines the contract for managing and persisting rules.
The Rule Registry allows rules to be stored, versioned, and retrieved by ID, moving RuleForge from a stateless API to a stateful managed service.
The Core Engine remains completely unaware of the storage mechanism (PostgreSQL, Memory, etc.).

## 1. Rule Object Model
A registered rule contains the following metadata:
- `rule_id` (string): Unique identifier for the rule (e.g., "adult_check").
- `version` (int): Auto-incremented version number for this rule_id.
- `language_version` (int): The RuleForge language version this rule was written for.
- `source` (string): The RuleForge source code.
- `status` (enum): The lifecycle state. Allowed: "DRAFT", "ACTIVE", "ARCHIVED".
- `created_at` (datetime): Timestamp of creation.
- `updated_at` (datetime): Timestamp of last update.

## 2. Lifecycle & Versioning Rules
- **Immutability:** `save_rule()` ALWAYS creates a new version. It never UPDATEs an existing source.
- **Single Active:** There can be AT MOST ONE `ACTIVE` version per `rule_id`.
- **Archival (Delete):** `delete_rule()` is a logical archival operation. It sets the latest version's status to `ARCHIVED`. It does NOT perform a physical DB delete, preserving historical determinism.

## 3. Determinism Guarantee
Fetching a rule by `rule_id` and `version` MUST always return the exact same `source` and `language_version`.

## 4. Async Rule Repository Protocol
The API will use a repository pattern to abstract storage.
Because PostgreSQL (asyncpg) is async, the protocol MUST be async to avoid sync wrappers.

class RuleRepository(Protocol):
    async def get_rule(self, rule_id: str, version: int = None) -> Rule: ...
    async def save_rule(self, rule_id: str, source: str, language_version: int) -> Rule: ...
    async def list_rules(self, status: str = None) -> List[Rule]: ...
    async def archive_rule(self, rule_id: str) -> None: ...
