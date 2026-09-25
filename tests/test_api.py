import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import httpx
from ruleforge import app

transport = httpx.ASGITransport(app=app)

@pytest.fixture(scope="module")
def client():
    # Usamos el cliente asíncrono nativo de httpx, que es lo que Starlette/FastAPI recomienda
    with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c

SCHEMA = {"customer": {"age": "Integer", "active": "Boolean"}}
RULE = 'RULE adult_check LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END'

async def test_api_health(client):
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}

async def test_api_evaluate_valid_rule(client):
    payload = {"rules": RULE, "context": {"customer": {"age": 21}}, "context_schema": SCHEMA}
    res = await client.post("/v1/evaluate", json=payload)
    assert res.status_code == 200
    assert res.json()["decisions"][0]["matched"] == True

async def test_api_semantic_error(client):
    payload = {"rules": 'RULE r LANGUAGE 1 WHEN customer.age > "18" THEN ALLOW END', "context": {"customer": {"age": 21}}, "context_schema": SCHEMA}
    res = await client.post("/v1/evaluate", json=payload)
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "RF3001"

async def test_api_missing_rules_field(client):
    payload = {"context": {"customer": {"age": 21}}, "context_schema": SCHEMA}
    res = await client.post("/v1/evaluate", json=payload)
    assert res.status_code == 422

async def test_api_decimal_serialization(client):
    payload = {"rules": 'RULE r LANGUAGE 1 WHEN invoice.total == 100.50 THEN ALLOW END', "context": {"invoice": {"total": "100.50"}}, "context_schema": {"invoice": {"total": "Decimal"}}}
    res = await client.post("/v1/evaluate", json=payload)
    assert res.status_code == 200
    assert res.json()["decisions"][0]["matched"] == True
