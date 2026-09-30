"""V11.4 Block 2.3: Compiler vs Interpreter property testing.

Invariant: for any valid rule R and context C,
    Interpreter(R, C) == Compiler(R, C)

Both use the Python runtime. The compiler may fall back to the
interpreter for unsupported constructs; in that case, both paths
produce identical results by definition.

Covers the same 22 families as Block 2.2.
"""
import sys, os, copy
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.dirname(__file__))

import pytest
from hypothesis import given, settings, HealthCheck
from ruleforge import RuleEngine
from ruleforge.lexer import Lexer, LexerError
from ruleforge.parser import Parser, ParserError
from ruleforge.semantic import SemanticAnalyzer, SemanticError
from ruleforge.evaluator import EvaluatorError

from test_cross_language import cross_language_rule_and_context, SCHEMA, normalize


def get_result(rule, context, use_compiler):
    """Evaluar regla con Python RuleEngine (interprete o compilador)."""
    ctx = copy.deepcopy(context)
    try:
        engine = RuleEngine(SCHEMA, use_compiler=use_compiler)
        decisions = engine.evaluate(rule, ctx).decisions
        d = decisions[-1]
        actions = [{"action_type": a.action_type, "value": a.value, "payload": a.payload}
                   for a in d.actions]
        return {"code": None, "matched": d.matched, "actions": actions}
    except (LexerError, ParserError, SemanticError, EvaluatorError) as e:
        return {"code": e.code, "matched": False, "actions": []}


def normalize_result(result):
    """Normalizar resultado para comparacion."""
    return {
        "code": result["code"],
        "matched": result["matched"],
        "actions": [
            {
                "action_type": a["action_type"],
                "value": a["value"],
                "payload": normalize(a["payload"]),
            }
            for a in result["actions"]
        ]
    }


@given(cross_language_rule_and_context())
@settings(max_examples=1000, deadline=None,
          suppress_health_check=[HealthCheck.too_slow])
def test_interpreter_equals_compiler(rule_ctx):
    """Interprete y Compilador DEBEN producir el mismo resultado semantico.

    Compara: code, matched, action_type, value, payload.
    NO compara: trace, AST, representaciones internas.

    El compilador puede hacer fallback al interprete para construcciones
    no soportadas (ANY/ALL/FILTER/MAP, NullCheck, etc.). En esos casos,
    ambos caminos usan el interprete y producen resultados identicos.
    """
    rule, context = rule_ctx

    interp = get_result(rule, context, use_compiler=False)
    comp = get_result(rule, context, use_compiler=True)

    interp_n = normalize_result(interp)
    comp_n = normalize_result(comp)

    assert interp_n == comp_n, (
        f"Interpreter/Compiler mismatch:\n"
        f"  Interpreter: {interp_n}\n"
        f"  Compiler:    {comp_n}\n"
        f"  rule: {rule}\n"
        f"  context: {context}"
    )
