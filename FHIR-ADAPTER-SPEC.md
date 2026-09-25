# RuleForge FHIR Adapter Specification

Defines how FHIR resources (used in Vantari Health) map to RuleForge Context.

## 1. Supported V1 Resources
- Patient
- Observation

## 2. Context Mapping Schema
The FhirAdapter must output a RuleForge Context matching this schema:
{
  "patient": { "age": "Integer", "active": "Boolean" },
  "observation": { "code": "String", "value": "Decimal" }
}

## 3. Example Mapping
FHIR Input (Observation & Patient):
{
  "resourceType": "Patient",
  "active": true,
  "birthDate": "1956-05-20"
}
{
  "resourceType": "Observation",
  "code": { "coding": [{ "code": "8480-6" }] },
  "valueQuantity": { "value": 165 }
}

RuleForge Context Output:
{
  "patient": { "age": 67, "active": true },
  "observation": { "code": "8480-6", "value": 165.0 }
}
