import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from ruleforge import RuleForgeEngine
from adapters.fhir_adapter import FhirAdapter
from adapters.erp_adapter import ErpAdapter

# --- FHIR / Vantari Tests ---

FHIR_SCHEMA = {
    "patient": {"age": "Integer", "active": "Boolean"},
    "observation": {"code": "String", "value": "Decimal"}
}
fhir_engine = RuleForgeEngine(FHIR_SCHEMA)

def test_fhir_adapter_hypertension_alert():
    patient = {"resourceType": "Patient", "active": True, "birthDate": "1956-05-20"}
    observation = {
        "resourceType": "Observation",
        "code": {"coding": [{"code": "8480-6"}]},
        "valueQuantity": {"value": 165}
    }
    
    context = FhirAdapter.to_context(patient, observation)
    assert context["patient"]["age"] > 60
    assert context["observation"]["code"] == "8480-6"
    
    rule = 'RULE hypertension_alert LANGUAGE 1 WHEN observation.code == "8480-6" AND observation.value >= 140 THEN ALERT "High BP" END'
    decisions = fhir_engine.evaluate(rule, context)
    
    assert decisions[0].matched == True
    assert decisions[0].actions[0].action_type == "ALERT"

def test_fhir_adapter_missing_observation_value():
    patient = {"resourceType": "Patient", "active": False, "birthDate": "2000-01-01"}
    observation = {"resourceType": "Observation", "code": {"coding": [{"code": "8480-6"}]}}
    
    context = FhirAdapter.to_context(patient, observation)
    assert context["observation"]["value"] is None

# --- ERP / ContaFlow Tests ---

ERP_SCHEMA = {
    "customer": {"active": "Boolean", "credit_score": "Integer"},
    "invoice": {"total": "Decimal", "status": "String"}
}
erp_engine = RuleForgeEngine(ERP_SCHEMA)

def test_erp_adapter_invoice_approval():
    customer = {"active": True, "credit_score": 750}
    invoice = {"total": 150000.0, "status": "PENDING"}
    
    context = ErpAdapter.to_context(customer, invoice)
    assert context["invoice"]["total"] == 150000.0
    
    rule = '''
    RULE invoice_approval LANGUAGE 1
    WHEN invoice.total >= 100000 AND customer.active == true AND invoice.status == "PENDING"
    THEN APPLY "AUTO_APPROVE" ELSE ALERT "Manual review" END
    '''
    decisions = erp_engine.evaluate(rule, context)
    
    assert decisions[0].matched == True
    assert decisions[0].actions[0].action_type == "APPLY"

def test_erp_adapter_runtime_validation_fails_on_bad_data():
    customer = {"active": True, "credit_score": "EXCELLENT"} # String instead of Integer
    invoice = {"total": 150000.0, "status": "PENDING"}
    
    context = ErpAdapter.to_context(customer, invoice)
    
    rule = 'RULE r LANGUAGE 1 WHEN customer.credit_score > 700 THEN ALLOW END'
    with pytest.raises(Exception) as exc:
        erp_engine.evaluate(rule, context)
    assert "RF4003" in str(exc.value) # Invalid Runtime Context
