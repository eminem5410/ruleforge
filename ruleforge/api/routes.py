import json
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from decimal import Decimal
from datetime import date

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

@router.post("/evaluate")
def evaluate_rule(request: EvaluateRequest):
    try:
        engine = RuleForgeEngine(request.context_schema)
        decisions = engine.evaluate(request.rules, request.context, explain=request.explain)
        
        output = {"decisions": [d.to_dict() for d in decisions]}
        # Usamos nuestro encoder custom para garantirizar precisión Decimal y Date en el JSON final
        return JSONResponse(content=json.loads(json.dumps(output, cls=RuleForgeEncoder)))
        
    except (LexerError, ParserError, SemanticError, EvaluatorError) as e:
        error_output = {"error": {"code": e.code, "message": str(e)}}
        return JSONResponse(status_code=400, content=error_output)
    except Exception as e:
        error_output = {"error": {"code": "INTERNAL", "message": str(e)}}
        return JSONResponse(status_code=500, content=error_output)
