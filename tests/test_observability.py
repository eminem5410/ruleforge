import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import httpx
from ruleforge import app

transport = httpx.ASGITransport(app=app)

@pytest.fixture
async def client():
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c

async def test_metrics_endpoint(client):
    res = await client.get("/metrics")
    assert res.status_code == 200
    assert "ruleforge_requests_total" in res.text
    assert "ruleforge_evaluations_total" in res.text
