import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient
from ruleforge import app

client = TestClient(app)

SCHEMA = {"customer": {"age": "Integer", "active": "Boolean"}}
RULE = 'RULE adult_check LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END'

def test_api_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}

def test_api_evaluate_valid_rule():
    payload = {
        "rules": RULE,
        "context": {"customer": {"age": 21}},
        "context_schema": SCHEMA
    }
    res = client.post("/v1/evaluate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["decisions"][0]["rule_id"] == "adult_check"
    assert data["decisions"][0]["matched"] == True

def test_api_evaluate_semantic_error():
    payload = {
        "rules": 'RULE r LANGUAGE 1 WHEN customer.age > "18" THEN ALLOW END',
        "context": {"customer": {"age": 21}},
        "context_schema": SCHEMA
    }
    res = client.post("/v1/evaluate", json=payload)
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "RF3001"

def test_api_missing_rules_field():
    payload = {
        "context": {"customer": {"age": 21}},
        "context_schema": SCHEMA
    }
    res = client.post("/v1/evaluate", json=payload)
    # 422 Unprocessable Entity por validación de Pydantic
    assert res.status_code == 422 

def test_api_decimal_serialization():
    payload = {
        "rules": 'RULE r LANGUAGE 1 WHEN invoice.total == 100.50 THEN ALLOW END',
        "context": {"invoice": {"total": 100.50}},
        "context_schema": {"invoice": {"total": "Decimal"}}
    }
    res = client.post("/v1/evaluate", json=payload)
    assert res.status_code == 200
    # El trace debe mantener el decimal como string en el JSON final si está en el contexto
    # pero como no pedimos explain, solo validamos que no rompa la serialización
    assert res.json()["decisions"][0]["matched"] == True
