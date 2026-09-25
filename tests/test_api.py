import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient
from ruleforge import app

client = TestClient(app)

def test_api_health():
    res = client.get("/health")
    assert res.status_code == 200

def test_api_evaluate_integer():
    payload = {
        "rules": 'RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END',
        "context": {"customer": {"age": 21}},
        "context_schema": {"customer": {"age": "Integer"}}
    }
    res = client.post("/v1/evaluate", json=payload)
    assert res.status_code == 200
    assert res.json()["decisions"][0]["matched"] == True

def test_api_evaluate_decimal_normalization():
    payload = {
        "rules": 'RULE r LANGUAGE 1 WHEN invoice.total == 100.50 THEN ALLOW END',
        "context": {"invoice": {"total": "100.50"}}, # Enviado como string en JSON
        "context_schema": {"invoice": {"total": "Decimal"}}
    }
    res = client.post("/v1/evaluate", json=payload)
    assert res.status_code == 200
    assert res.json()["decisions"][0]["matched"] == True

def test_api_evaluate_boolean():
    payload = {
        "rules": 'RULE r LANGUAGE 1 WHEN customer.active == true THEN ALLOW END',
        "context": {"customer": {"active": True}},
        "context_schema": {"customer": {"active": "Boolean"}}
    }
    res = client.post("/v1/evaluate", json=payload)
    assert res.status_code == 200
    assert res.json()["decisions"][0]["matched"] == True

def test_api_evaluate_date_normalization():
    payload = {
        "rules": 'RULE r LANGUAGE 1 WHEN customer.birth_date > 1990-01-01 THEN ALLOW END',
        "context": {"customer": {"birth_date": "1995-05-20"}},
        "context_schema": {"customer": {"birth_date": "Date"}}
    }
    res = client.post("/v1/evaluate", json=payload)
    assert res.status_code == 200
    assert res.json()["decisions"][0]["matched"] == True

def test_api_evaluate_null():
    payload = {
        "rules": 'RULE r LANGUAGE 1 WHEN customer.email IS NULL THEN ALLOW END',
        "context": {"customer": {"email": None}},
        "context_schema": {"customer": {"email": "String"}}
    }
    res = client.post("/v1/evaluate", json=payload)
    assert res.status_code == 200
    assert res.json()["decisions"][0]["matched"] == True

def test_api_explain_trace():
    payload = {
        "rules": 'RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END',
        "context": {"customer": {"age": 21}},
        "context_schema": {"customer": {"age": "Integer"}},
        "explain": True
    }
    res = client.post("/v1/evaluate", json=payload)
    assert res.status_code == 200
    trace = res.json()["decisions"][0]["trace"][0]
    assert trace["type"] == "comparison"

def test_api_semantic_error_400():
    payload = {
        "rules": 'RULE r LANGUAGE 1 WHEN customer.age > "18" THEN ALLOW END',
        "context": {"customer": {"age": 21}},
        "context_schema": {"customer": {"age": "Integer"}}
    }
    res = client.post("/v1/evaluate", json=payload)
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "RF3001"

def test_api_runtime_error_400():
    payload = {
        "rules": 'RULE r LANGUAGE 1 WHEN invoice.total / 0 > 10 THEN ALLOW END',
        "context": {"invoice": {"total": "100.0"}},
        "context_schema": {"invoice": {"total": "Decimal"}}
    }
    res = client.post("/v1/evaluate", json=payload)
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "RF4001"

def test_api_missing_rules_field_422():
    payload = {"context": {}, "context_schema": {}}
    res = client.post("/v1/evaluate", json=payload)
    assert res.status_code == 422
