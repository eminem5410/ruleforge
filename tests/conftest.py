import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from ruleforge import app
from ruleforge.auth.dependencies import get_api_key
from opentelemetry import trace

@pytest.fixture(scope="session", autouse=True)
def shutdown_otel():
    # Fuerza el flush de spans antes de que pytest cierre los streams
    yield
    provider = trace.get_tracer_provider()
    if hasattr(provider, 'shutdown'):
        provider.shutdown()

@pytest.fixture(autouse=True)
def override_auth(request):
    if "test_auth" not in request.node.name:
        async def bypass():
            from ruleforge.auth.models import ApiKey
            from datetime import datetime
            return ApiKey(id="test", key_hash="test", name="test", status="ACTIVE", scopes=["rules:read", "rules:write", "rules:activate", "rules:evaluate", "rules:admin"], created_at=datetime.now())
        app.dependency_overrides[get_api_key] = bypass
    yield
    app.dependency_overrides.clear()
