from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from ..registry.in_memory_repository import InMemoryRuleRepository
from .. import RuleForgeEngine
from ..lexer import LexerError
from ..parser import ParserError
from ..semantic import SemanticError
from ..evaluator import EvaluatorError
import json
from decimal import Decimal
from datetime import date
import copy

router = APIRouter()
repo = InMemoryRuleRepository()  # Singleton simple para V4.0.0

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

@router.post("/rules", status_code=201)
def create_rule(request: CreateRuleRequest):
    try:
        rule = repo.save_rule(request.rule_id, request.source, request.language_version)
        return rule.model_dump()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/rules/{rule_id}")
def get_rule(rule_id: str):
    try:
        rule = repo.get_rule(rule_id)
        return rule.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/rules/{rule_id}/evaluate")
def evaluate_registered_rule(rule_id: str, request: EvaluateRegisteredRuleRequest):
    try:
        rule = repo.get_rule(rule_id)
        
        # 1. Immutabilidad: Deep copy
        ctx_copy = copy.deepcopy(request.context)
        
        # 2. Normalizar Decimals (igual que en /evaluate)
        for obj_name, props in request.context_schema.items():
            if obj_name in ctx_copy and isinstance(ctx_copy[obj_name], dict):
                for prop_name, prop_type in props.items():
                    if prop_name in ctx_copy[obj_name]:
                        val = ctx_copy[obj_name][prop_name]
                        if val is not None and prop_type == "Decimal" and not isinstance(val, Decimal):
                            ctx_copy[obj_name][prop_name] = Decimal(str(val))
        
        # 3. Evaluate
        engine = RuleForgeEngine(request.context_schema)
        decisions = engine.evaluate(rule.source, ctx_copy, explain=request.explain)
        
        output = {"decisions": [d.to_dict() for d in decisions]}
        return json.loads(json.dumps(output, cls=RuleForgeEncoder))
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (LexerError, ParserError, SemanticError, EvaluatorError) as e:
        return {"error": {"code": e.code, "message": str(e)}}
    except Exception as e:
        return {"error": {"code": "INTERNAL", "message": "Internal server error"}}
