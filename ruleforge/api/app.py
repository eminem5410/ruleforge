from fastapi import FastAPI
from contextlib import asynccontextmanager
from importlib.metadata import version as pkg_version
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from .routes import router as evaluate_router
from .registry_routes import router as registry_router, init_db
from .observability import setup_logging, setup_tracing, metrics_middleware

try:
    app_version = pkg_version("ruleforge")
except Exception:
    app_version = "0.0.0"

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    await init_db()
    yield

app = FastAPI(title="RuleForge API", version=app_version, lifespan=lifespan)

# Instrumentar OpenTelemetry
setup_tracing(app)

# Middleware para Prometheus
app.middleware("http")(metrics_middleware)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/metrics")
def metrics():
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

app.include_router(evaluate_router, prefix="/v1")
app.include_router(registry_router, prefix="/v1")
