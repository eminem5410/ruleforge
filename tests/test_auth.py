import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import httpx
from ruleforge import app
from ruleforge.auth.dependencies import get_api_key_test, _repo_instance

transport = httpx.ASGITransport(app=app)

@pytest.fixture(scope="module")
async def unauth_client():
    # Cliente SIN el bypass de auth (para probar 401)
    from fastapi.testclient import TestClient
    # Usamos httpx async nativo
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c

@pytest.fixture(scope="module")
async def auth_client():
    # Cliente CON el bypass de auth (para probar que la lógica de negocio funcione si tenés permisos)
    from fastapi.testclient import TestClient
    app.dependency_overrides[get_api_key_test] = get_api_key_test # Bypass
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
    app.dependency_overrides.clear()

# Para probar tokens reales, vamos a crear uno en el repo en memoria
@pytest.mark.asyncio
async def setup_token(scopes):
    import hashlib
    plaintext = "rf_live_test_" + scopes[0]
    key_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    await _repo_instance.create(key_hash=key_hash, name="Test Key", scopes=scopes)
    return plaintext

async def test_auth_001_unauthenticated_rejected(unauth_client):
    res = await unauth_client.get("/v1/rules/test")
    assert res.status_code == 401

async def test_auth_002_valid_api_key_accepted(unauth_client):
    token = await setup_token(["rules:read"])
    res = await unauth_client.get("/v1/rules/test", headers={"Authorization": f"Bearer {token}"})
    # 404 because rule doesn't exist, but it passed auth!
    assert res.status_code == 404 

async def test_auth_003_invalid_api_key_rejected(unauth_client):
    res = await unauth_client.get("/v1/rules/test", headers={"Authorization": "Bearer invalid_token"})
    assert res.status_code == 401

async def test_auth_006_missing_scope_rejected(unauth_client):
    # Token with only rules:read trying to POST
    token = await setup_token(["rules:read"])
    res = await unauth_client.post("/v1/rules", json={"rule_id": "x", "source": "...", "language_version": 1}, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403

async def test_auth_008_write_scope_accepted(unauth_client):
    token = await setup_token(["rules:write"])
    res = await unauth_client.post("/v1/rules", json={"rule_id": "auth_test", "source": "RULE r LANGUAGE 1 WHEN true THEN ALLOW END", "language_version": 1}, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 201

async def test_auth_016_hash_never_returned(unauth_client):
    token = await setup_token(["rules:admin"])
    res = await unauth_client.post("/v1/api-keys", json={"name": "New Key", "scopes": ["rules:read"]}, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert "key_hash" not in res.json()
