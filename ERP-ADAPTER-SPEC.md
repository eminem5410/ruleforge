# RuleForge ERP Adapter Specification

Defines how ERP entities (used in ContaFlow) map to RuleForge Context.

## 1. Supported V1 Entities
- Customer
- Invoice

## 2. Context Mapping Schema
The ErpAdapter must output a RuleForge Context matching this schema:
{
  "customer": { "active": "Boolean", "credit_score": "Integer" },
  "invoice": { "total": "Decimal", "status": "String" }
}

## 3. Example Mapping
ERP Input (Database Models / DTOs):
Customer(id=123, active=True, credit_score=750)
Invoice(id=456, total=150000.0, status="PENDING")

RuleForge Context Output:
{
  "customer": { "active": true, "credit_score": 750 },
  "invoice": { "total": 150000.0, "status": "PENDING" }
}
