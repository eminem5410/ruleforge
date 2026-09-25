import os
from fastapi import APIRouter, HTTPException, Depends, Security
from pydantic import BaseModel
from typing import Dict, Any, Annotated
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from ..registry.in_memory_repository import InMemoryRuleRepository
from ..registry.postgres_repository import PostgresRuleRepository
from ..registry.repository import RuleRepository
from ..persistence.models import Base
from .. import RuleForgeEngine
from ..lexer import LexerError
from ..parser import ParserError
from ..semantic import SemanticError
from ..evaluator import EvaluatorError
from ..auth.dependencies import require_scope
from ..auth.models import ApiKey
import json
from decimal import Decimal
from datetime import date
import copy
import hashlib
import uuid

router = APIRouter()

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    engine = create_async_engine(DATABASE_URL, echo=False)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    _repo_instance = PostgresRuleRepository(SessionLocal)
    from ..auth.repository import PostgresApiKeyRepository
    _api_key_repo = PostgresApiKeyRepository(SessionLocal)
else:
    _repo_instance = InMemoryRuleRepository()
    from ..auth.repository import InMemoryApiKeyRepository
    _api_key_repo = InMemoryApiKeyRepository()

async def get_repository() -> RuleRepository:
    return _repo_instance

async def init_db():
    if DATABASE_URL:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

class RuleForgeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal): return str(obj)
        if isinstance(obj, date): return obj.isoformat()
        return super().default(obj)

class CreateRuleRequest(BaseModel):
    rule_id: str
    source: str
    language_version: int

class EvaluateRegisteredRuleRequest(BaseModel):
    context: Dict[str, Any]
    context_schema: Dict[str, Dict[str, str]]
    explain: bool = False

class CreateApiKeyRequest(BaseModel):
    name: str
    scopes: list[str]

@router.post("/rules", status_code=201, dependencies=[Depends(require_scope("rules:write"))])
async def create_rule(request: CreateRuleRequest, repo: Annotated[RuleRepository, Depends(get_repository)]):
    try:
        rule = await repo.save_rule(request.rule_id, request.source, request.language_version)
        return rule.model_dump()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/rules/{rule_id}", dependencies=[Depends(require_scope("rules:read"))])
async def get_rule(rule_id: str, repo: Annotated[RuleRepository, Depends(get_repository)]):
    try:
        rule = await repo.get_rule(rule_id)
        return rule.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/rules/{rule_id}/versions/{version}/activate", dependencies=[Depends(require_scope("rules:activate"))])
async def activate_rule(rule_id: str, version: int, repo: Annotated[RuleRepository, Depends(get_repository)]):
    try:
        rule = await repo.activate_rule(rule_id, version)
        return rule.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/rules/{rule_id}", dependencies=[Depends(require_scope("rules:admin"))])
async def archive_rule(rule_id: str, repo: Annotated[RuleRepository, Depends(get_repository)]):
    try:
        await repo.archive_rule(rule_id)
        return {"status": "archived"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/rules/{rule_id}/evaluate", dependencies=[Depends(require_scope("rules:evaluate"))])
async def evaluate_registered_rule(rule_id: str, request: EvaluateRegisteredRuleRequest, repo: Annotated[RuleRepository, Depends(get_repository)]):
    try:
        rule = await repo.get_rule(rule_id)
        ctx_copy = copy.deepcopy(request.context)
        for obj_name, props in request.context_schema.items():
            if obj_name in ctx_copy and isinstance(ctx_copy[obj_name], dict):
                for prop_name, prop_type in props.items():
                    if prop_name in ctx_copy[obj_name]:
                        val = ctx_copy[obj_name][prop_name]
                        if val is not None and prop_type == "Decimal" and not isinstance(val, Decimal):
                            ctx_copy[obj_name][prop_name] = Decimal(str(val))
        engine = RuleForgeEngine(request.context_schema)
        decisions = engine.evaluate(rule.source, ctx_copy, explain=request.explain)
        output = {"decisions": [d.to_dict() for d in decisions]}
        return json.loads(json.dumps(output, cls=RuleForgeEncoder))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (LexerError, ParserError, SemanticError, EvaluatorError) as e:
        return {"error": {"code": e.code, "message": str(e)}}
    except Exception:
        return {"error": {"code": "INTERNAL", "message": "Internal server error"}}

# --- API Key Management Endpoint (Admin only) ---
@router.post("/api-keys", dependencies=[Depends(require_scope("rules:admin"))])
async def create_api_key(request: CreateApiKeyRequest):
    import secrets
    plaintext = "rf_live_" + secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    
    api_key = await _api_key_repo.create(key_hash=key_hash, name=request.name, scopes=request.scopes)
    return {"id": api_key.id, "name": api_key.name, "scopes": api_key.scopes, "plaintext_key": plaintext}
