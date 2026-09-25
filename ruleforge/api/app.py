from fastapi import FastAPI
from importlib.metadata import version as pkg_version
from .routes import router

try:
    app_version = pkg_version("ruleforge")
except Exception:
    app_version = "0.0.0"

app = FastAPI(title="RuleForge API", version=app_version)

@app.get("/health")
def health_check():
    return {"status": "ok"}

app.include_router(router, prefix="/v1")
