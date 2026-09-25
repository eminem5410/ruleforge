from fastapi import FastAPI
from contextlib import asynccontextmanager
from importlib.metadata import version as pkg_version
from .routes import router as evaluate_router
from .registry_routes import router as registry_router, init_db

try:
    app_version = pkg_version("ruleforge")
except Exception:
    app_version = "0.0.0"

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="RuleForge API", version=app_version, lifespan=lifespan)

@app.get("/health")
def health_check():
    return {"status": "ok"}

app.include_router(evaluate_router, prefix="/v1")
app.include_router(registry_router, prefix="/v1")
