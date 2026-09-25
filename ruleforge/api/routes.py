import json
import copy
import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from importlib.metadata import version as pkg_version

from .. import RuleForgeEngine
from ..lexer import LexerError
from ..parser import ParserError
from ..semantic import SemanticError
from ..evaluator import EvaluatorError
from ..auth.dependencies import require_scope
from .models import EvaluateRequest

router = APIRouter()
logger = logging.getLogger("ruleforge")

class RuleForgeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal): return str(obj)
        if isinstance(obj, date): return obj.isoformat()
        return super().default(obj)

def normalize_context(context: dict, schema: dict) -> dict:
    for obj_name, props in schema.items():
        if obj_name in context and isinstance(context[obj_name], dict):
            for prop_name, prop_type in props.items():
                if prop_name in context[obj_name]:
                    val = context[obj_name][prop_name]
                    if val is None: continue
                    try:
                        if prop_type == "Decimal" and not isinstance(val, Decimal):
                            context[obj_name][prop_name] = Decimal(str(val))
                    except (InvalidOperation, ValueError):
                        raise EvaluatorError("RF4003", f"Invalid Runtime Context: Cannot normalize '{obj_name}.{prop_name}' to Decimal: {val}")
    return context

@router.post("/evaluate", dependencies=[Depends(require_scope("rules:evaluate"))])
def evaluate_rule(request: EvaluateRequest):
    try:
        ctx_copy = copy.deepcopy(request.context)
        normalized_context = normalize_context(ctx_copy, request.context_schema)
        engine = RuleForgeEngine(request.context_schema)
        decisions = engine.evaluate(request.rules, normalized_context, explain=request.explain)
        output = {"decisions": [d.to_dict() for d in decisions]}
        return JSONResponse(content=json.loads(json.dumps(output, cls=RuleForgeEncoder)))
    except (LexerError, ParserError, SemanticError, EvaluatorError) as e:
        error_output = {"error": {"code": e.code, "message": str(e)}}
        return JSONResponse(status_code=400, content=error_output)
    except Exception as e:
        logger.exception("Internal server error during evaluation")
        error_output = {"error": {"code": "INTERNAL", "message": "Internal server error"}}
        return JSONResponse(status_code=500, content=error_output)
