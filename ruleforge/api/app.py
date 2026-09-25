from fastapi import FastAPI
from .routes import router

app = FastAPI(title="RuleForge API", version="3.0.0")

@app.get("/health")
def health_check():
    return {"status": "ok"}

app.include_router(router, prefix="/v1")
