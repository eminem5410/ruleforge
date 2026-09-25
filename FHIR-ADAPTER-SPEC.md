# RuleForge FHIR Adapter Specification

Defines how FHIR resources (used in Vantari Health) map to RuleForge Context.
The RuleForge Core only sees the "RuleForge Context" section. It knows nothing about FHIR.

## 1. Supported Resources (V2.2.0)
- Patient
- Observation
- AllergyIntolerance
- MedicationRequest
- MedicationDispense
- Encounter

## 2. Context Mapping Schema & Rules
The FhirAdapter must output a RuleForge Context matching this schema.
Missing fields in FHIR resources MUST be mapped to `None` (NULL).

{
  "patient": { "age": "Integer", "active": "Boolean" },
  "observation": { "code": "String", "value": "Decimal" },
  "allergy": { "code": "String", "status": "String" },
  "medication": { "code": "String", "status": "String" },
  "dispense": { "code": "String", "status": "String" },
  "encounter": { "status": "String", "class": "String" }
}

## 3. Detailed Mappings

### Patient
FHIR Input: { "resourceType": "Patient", "active": true, "birthDate": "1956-05-20" }
RuleForge Context: { "patient": { "age": 67, "active": true } }
Note: `age` requires a deterministic `reference_date` to be calculated.

### Observation
FHIR Input: { "resourceType": "Observation", "code": { "coding": [{ "code": "8480-6" }] }, "valueQuantity": { "value": 165 } }
RuleForge Context: { "observation": { "code": "8480-6", "value": 165.0 } }

### AllergyIntolerance (NEW)
FHIR Input: { "resourceType": "AllergyIntolerance", "code": { "coding": [{ "code": "A01" }] }, "clinicalStatus": { "coding": [{ "code": "active" }] } }
RuleForge Context: { "allergy": { "code": "A01", "status": "active" } }

### MedicationRequest (NEW)
FHIR Input: { "resourceType": "MedicationRequest", "medicationCodeableConcept": { "coding": [{ "code": "M01" }] }, "status": "active" }
RuleForge Context: { "medication": { "code": "M01", "status": "active" } }

### MedicationDispense (NEW)
FHIR Input: { "resourceType": "MedicationDispense", "medicationCodeableConcept": { "coding": [{ "code": "D01" }] }, "status": "completed" }
RuleForge Context: { "dispense": { "code": "D01", "status": "completed" } }

### Encounter (NEW)
FHIR Input: { "resourceType": "Encounter", "status": "finished", "class": { "code": "AMB" } }
RuleForge Context: { "encounter": { "status": "finished", "class": "AMB" } }
