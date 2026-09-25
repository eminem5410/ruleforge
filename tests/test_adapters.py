import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from datetime import date
from decimal import Decimal
from ruleforge import RuleForgeEngine
from ruleforge.evaluator import EvaluatorError
from adapters.fhir_adapter import FhirAdapter
from adapters.erp_adapter import ErpAdapter

# --- FHIR / Vantari Tests ---

FHIR_SCHEMA = {
    "patient": {"age": "Integer", "active": "Boolean"},
    "observation": {"code": "String", "value": "Decimal"}
}
fhir_engine = RuleForgeEngine(FHIR_SCHEMA)
REFERENCE_DATE = date(2024, 1, 1) # Fecha fija para determinismo

def test_fhir_adapter_determinism_and_precision():
    patient = {"resourceType": "Patient", "active": True, "birthDate": "1956-05-20"}
    observation = {
        "resourceType": "Observation",
        "code": {"coding": [{"code": "8480-6"}]},
        "valueQuantity": {"value": 165} # Viene como int
    }
    
    context = FhirAdapter.to_context(patient, observation, reference_date=REFERENCE_DATE)
    
    # Determinismo: La edad debe ser exacta y no depender de hoy
    assert context["patient"]["age"] == 67
    # Precisión: El valor debe ser Decimal, no float
    assert context["observation"]["value"] == Decimal("165")
    assert isinstance(context["observation"]["value"], Decimal)
    
    rule = 'RULE hypertension_alert LANGUAGE 1 WHEN observation.code == "8480-6" AND observation.value >= 140 THEN ALERT "High BP" END'
    decisions = fhir_engine.evaluate(rule, context)
    assert decisions[0].matched == True

def test_fhir_adapter_missing_active_is_null():
    patient = {"resourceType": "Patient", "birthDate": "2000-01-01"} # Falta 'active'
    observation = {"resourceType": "Observation", "code": {"coding": [{"code": "8480-6"}]}}
    
    context = FhirAdapter.to_context(patient, observation, reference_date=REFERENCE_DATE)
    # Active debe ser None (NULL), no False
    assert context["patient"]["active"] is None
    
    rule = 'RULE r LANGUAGE 1 WHEN patient.active IS NULL THEN ALLOW END'
    decisions = fhir_engine.evaluate(rule, context)
    assert decisions[0].matched == True

def test_fhir_adapter_missing_reference_date_fails():
    patient = {"resourceType": "Patient", "birthDate": "2000-01-01"}
    observation = {"resourceType": "Observation"}
    with pytest.raises(ValueError):
        FhirAdapter.to_context(patient, observation) # Sin reference_date

# --- ERP / ContaFlow Tests ---

ERP_SCHEMA = {
    "customer": {"active": "Boolean", "credit_score": "Integer"},
    "invoice": {"total": "Decimal", "status": "String"}
}
erp_engine = RuleForgeEngine(ERP_SCHEMA)

def test_erp_adapter_precision_and_missing_data():
    customer = {"active": True} # Falta credit_score
    invoice = {"total": "150000.50", "status": "PENDING"} # Total viene como string
    
    context = ErpAdapter.to_context(customer, invoice)
    
    # Precisión: Decimal exacto desde string
    assert context["invoice"]["total"] == Decimal("150000.50")
    # Missing data: credit_score es NULL
    assert context["customer"]["credit_score"] is None
    
    rule = 'RULE r LANGUAGE 1 WHEN customer.credit_score IS NULL THEN ALLOW END'
    decisions = erp_engine.evaluate(rule, context)
    assert decisions[0].matched == True

def test_erp_adapter_runtime_validation_fails_on_bad_data():
    customer = {"active": True, "credit_score": "EXCELLENT"} # String instead of Integer
    invoice = {"total": 150000.0, "status": "PENDING"}
    
    context = ErpAdapter.to_context(customer, invoice)
    
    rule = 'RULE r LANGUAGE 1 WHEN customer.credit_score > 700 THEN ALLOW END'
    with pytest.raises(EvaluatorError) as exc:
        erp_engine.evaluate(rule, context)
    assert exc.value.code == "RF4003"

# --- FHIR V2.2.0 Expansion Tests ---

FHIR_SCHEMA_V2 = {
    "patient": {"age": "Integer", "active": "Boolean"},
    "observation": {"code": "String", "value": "Decimal"},
    "allergy": {"code": "String", "status": "String"},
    "medication": {"code": "String", "status": "String"},
    "dispense": {"code": "String", "status": "String"},
    "encounter": {"status": "String", "class": "String"}
}
fhir_engine_v2 = RuleForgeEngine(FHIR_SCHEMA_V2)

def test_fhir_adapter_allergy_intolerance():
    patient = {"resourceType": "Patient", "birthDate": "2000-01-01"}
    observation = {}
    allergy = {
        "resourceType": "AllergyIntolerance",
        "code": {"coding": [{"code": "A01"}]},
        "clinicalStatus": {"coding": [{"code": "active"}]}
    }
    
    context = FhirAdapter.to_context(patient, observation, reference_date=REFERENCE_DATE, allergy_resource=allergy)
    assert context["allergy"]["code"] == "A01"
    assert context["allergy"]["status"] == "active"
    
    rule = 'RULE r LANGUAGE 1 WHEN allergy.status == "active" THEN ALERT "Active Allergy" END'
    decisions = fhir_engine_v2.evaluate(rule, context)
    assert decisions[0].matched == True

def test_fhir_adapter_medication_request():
    patient = {"resourceType": "Patient", "birthDate": "2000-01-01"}
    observation = {}
    medication = {
        "resourceType": "MedicationRequest",
        "medicationCodeableConcept": {"coding": [{"code": "M01"}]},
        "status": "active"
    }
    
    context = FhirAdapter.to_context(patient, observation, reference_date=REFERENCE_DATE, medication_resource=medication)
    assert context["medication"]["code"] == "M01"
    assert context["medication"]["status"] == "active"

def test_fhir_adapter_medication_dispense():
    patient = {"resourceType": "Patient", "birthDate": "2000-01-01"}
    observation = {}
    dispense = {
        "resourceType": "MedicationDispense",
        "medicationCodeableConcept": {"coding": [{"code": "D01"}]},
        "status": "completed"
    }
    
    context = FhirAdapter.to_context(patient, observation, reference_date=REFERENCE_DATE, dispense_resource=dispense)
    assert context["dispense"]["code"] == "D01"
    assert context["dispense"]["status"] == "completed"

def test_fhir_adapter_encounter():
    patient = {"resourceType": "Patient", "birthDate": "2000-01-01"}
    observation = {}
    encounter = {
        "resourceType": "Encounter",
        "status": "finished",
        "class": {"code": "AMB"}
    }
    
    context = FhirAdapter.to_context(patient, observation, reference_date=REFERENCE_DATE, encounter_resource=encounter)
    assert context["encounter"]["status"] == "finished"
    assert context["encounter"]["class"] == "AMB"

def test_fhir_adapter_missing_allergy_fields_are_null():
    patient = {"resourceType": "Patient", "birthDate": "2000-01-01"}
    observation = {}
    allergy = {"resourceType": "AllergyIntolerance"} # Faltan code y status
    
    context = FhirAdapter.to_context(patient, observation, reference_date=REFERENCE_DATE, allergy_resource=allergy)
    assert context["allergy"]["code"] is None
    assert context["allergy"]["status"] is None
