import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import httpx
import ruleforge
from ruleforge import app

transport = httpx.ASGITransport(app=app)

@pytest.fixture(scope="module")
async def client():
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c

SCHEMA = {"customer": {"age": "Integer", "active": "Boolean"}}
RULE = 'RULE adult_check LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END'

async def test_api_001_health(client):
    res = await client.get("/health")
    assert res.status_code == 200

async def test_api_002_valid_evaluation(client):
    payload = {"rules": RULE, "context": {"customer": {"age": 21}}, "context_schema": SCHEMA}
    res = await client.post("/v1/evaluate", json=payload)
    assert res.status_code == 200
    assert res.json()["decisions"][0]["matched"] == True

async def test_api_003_semantic_error(client):
    payload = {"rules": 'RULE r LANGUAGE 1 WHEN customer.age > "18" THEN ALLOW END', "context": {"customer": {"age": 21}}, "context_schema": SCHEMA}
    res = await client.post("/v1/evaluate", json=payload)
    assert res.status_code == 400

async def test_api_004_missing_required_field(client):
    payload = {"context": {"customer": {"age": 21}}, "context_schema": SCHEMA}
    res = await client.post("/v1/evaluate", json=payload)
    assert res.status_code == 422

async def test_api_005_decimal_serialization(client):
    payload = {"rules": 'RULE r LANGUAGE 1 WHEN invoice.total == 100.50 THEN ALLOW END', "context": {"invoice": {"total": "100.50"}}, "context_schema": {"invoice": {"total": "Decimal"}}}
    res = await client.post("/v1/evaluate", json=payload)
    assert res.status_code == 200

async def test_api_006_explain_mode(client):
    payload = {"rules": RULE, "context": {"customer": {"age": 21}}, "context_schema": SCHEMA, "explain": True}
    res = await client.post("/v1/evaluate", json=payload)
    assert res.status_code == 200
    assert res.json()["decisions"][0]["trace"][0]["type"] == "comparison"

async def test_api_007_invalid_decimal_format(client):
    payload = {"rules": 'RULE r LANGUAGE 1 WHEN invoice.total == 100.50 THEN ALLOW END', "context": {"invoice": {"total": "NOT_A_NUMBER"}}, "context_schema": {"invoice": {"total": "Decimal"}}}
    res = await client.post("/v1/evaluate", json=payload)
    assert res.status_code == 400

async def test_api_008_invalid_context_structure(client):
    payload = {"rules": RULE, "context": [], "context_schema": SCHEMA}
    res = await client.post("/v1/evaluate", json=payload)
    assert res.status_code == 422

async def test_api_009_invalid_schema_type(client):
    payload = {"rules": RULE, "context": {"customer": {"age": 21}}, "context_schema": {"customer": {"age": "Float"}}}
    res = await client.post("/v1/evaluate", json=payload)
    assert res.status_code == 422

async def test_api_010_invalid_schema_structure(client):
    payload = {"rules": RULE, "context": {"customer": {"age": 21}}, "context_schema": []}
    res = await client.post("/v1/evaluate", json=payload)
    assert res.status_code == 422

async def test_api_011_internal_error_sanitization(client, monkeypatch):
    def mock_evaluate(*args, **kwargs):
        raise Exception("Secret internal error details")
    monkeypatch.setattr(ruleforge.RuleForgeEngine, "evaluate", mock_evaluate)
    payload = {"rules": RULE, "context": {"customer": {"age": 21}}, "context_schema": SCHEMA}
    res = await client.post("/v1/evaluate", json=payload)
    assert res.status_code == 500
    assert res.json()["error"]["message"] == "Internal server error"

async def test_api_012_null_handling(client):
    payload = {"rules": 'RULE r LANGUAGE 1 WHEN customer.email IS NULL THEN ALLOW END', "context": {"customer": {"email": None}}, "context_schema": {"customer": {"email": "String"}}}
    res = await client.post("/v1/evaluate", json=payload)
    assert res.status_code == 200

async def test_api_013_date_serialization(client):
    payload = {"rules": 'RULE r LANGUAGE 1 WHEN customer.birth_date > 1990-01-01 THEN ALLOW END', "context": {"customer": {"birth_date": "1995-05-20"}}, "context_schema": {"customer": {"birth_date": "Date"}}}
    res = await client.post("/v1/evaluate", json=payload)
    assert res.status_code == 200

# --- V4.0.0 Registry API Tests ---

async def test_api_create_rule(client):
    payload = {"rule_id": "adult_check", "source": RULE, "language_version": 1}
    res = await client.post("/v1/rules", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["rule_id"] == "adult_check"
    assert data["version"] == 1

async def test_api_activate_rule(client):
    res = await client.post("/v1/rules/adult_check/versions/1/activate")
    assert res.status_code == 200
    assert res.json()["status"] == "ACTIVE"

async def test_api_get_rule(client):
    res = await client.get("/v1/rules/adult_check")
    assert res.status_code == 200
    assert res.json()["rule_id"] == "adult_check"

async def test_api_evaluate_registered_rule(client):
    payload = {"context": {"customer": {"age": 21}}, "context_schema": SCHEMA}
    res = await client.post("/v1/rules/adult_check/evaluate", json=payload)
    assert res.status_code == 200
    assert res.json()["decisions"][0]["matched"] == True
