import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from opentelemetry import trace

@pytest.fixture(scope="session", autouse=True)
def shutdown_otel():
    yield
    provider = trace.get_tracer_provider()
    if hasattr(provider, 'shutdown'):
        provider.shutdown()

@pytest.fixture(autouse=True)
def override_auth(request):
    # Si el módulo del test no importó la 'app' de FastAPI, no aplicamos el override.
    # Esto desacopla perfectamente los tests de Core/REPL de los de API.
    if not hasattr(request.module, 'app'):
        yield
        return

    from ruleforge.auth.dependencies import get_api_key
    app = request.module.app

    if "test_auth" not in request.node.name:
        async def bypass():
            from ruleforge.auth.models import ApiKey
            from datetime import datetime
            return ApiKey(id="test", key_hash="test", name="test", status="ACTIVE", scopes=["rules:read", "rules:write", "rules:activate", "rules:evaluate", "rules:admin"], created_at=datetime.now())
        app.dependency_overrides[get_api_key] = bypass
    yield
    app.dependency_overrides.clear()
