import json
from datetime import date
from decimal import Decimal, InvalidOperation
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from .. import RuleForgeEngine
from ..lexer import LexerError
from ..parser import ParserError
from ..semantic import SemanticError
from ..evaluator import EvaluatorError
from .models import EvaluateRequest

router = APIRouter()

class RuleForgeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal): return str(obj)
        if isinstance(obj, date): return obj.isoformat()
        return super().default(obj)

def normalize_context(context: dict, schema: dict) -> dict:
    """Normalizes JSON types to Python Core types based on the schema."""
    for obj_name, props in schema.items():
        if obj_name in context and isinstance(context[obj_name], dict):
            for prop_name, prop_type in props.items():
                if prop_name in context[obj_name]:
                    val = context[obj_name][prop_name]
                    if val is None:
                        continue
                        
                    try:
                        # Solo normalizamos Decimal, ya que el Core espera el tipo nativo.
                        # Date se pasa como string porque el Core (engine.py) ya lo convierte a date object.
                        if prop_type == "Decimal" and not isinstance(val, Decimal):
                            context[obj_name][prop_name] = Decimal(str(val))
                    except InvalidOperation:
                        raise EvaluatorError("RF4003", f"Invalid Runtime Context: Cannot normalize '{obj_name}.{prop_name}' to Decimal: {val}")
    return context

@router.post("/evaluate")
def evaluate_rule(request: EvaluateRequest):
    try:
        # 1. Normalize HTTP JSON types to Core Python Types
        normalized_context = normalize_context(request.context, request.context_schema)
        
        # 2. Evaluate
        engine = RuleForgeEngine(request.context_schema)
        decisions = engine.evaluate(request.rules, normalized_context, explain=request.explain)
        
        # 3. Serialize back to JSON
        output = {"decisions": [d.to_dict() for d in decisions]}
        return JSONResponse(content=json.loads(json.dumps(output, cls=RuleForgeEncoder)))
        
    except (LexerError, ParserError, SemanticError, EvaluatorError) as e:
        error_output = {"error": {"code": e.code, "message": str(e)}}
        return JSONResponse(status_code=400, content=error_output)
    except Exception as e:
        error_output = {"error": {"code": "INTERNAL", "message": str(e)}}
        return JSONResponse(status_code=500, content=error_output)
