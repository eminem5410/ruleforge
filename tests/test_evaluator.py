import sys
import os
from datetime import date
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from ruleforge.lexer import Lexer
from ruleforge.parser import Parser
from ruleforge.semantic import SemanticAnalyzer
from ruleforge.evaluator import Evaluator, EvaluatorError

SCHEMA = {
    "customer": {"age": "Integer", "name": "String", "active": "Boolean", "email": "String", "birth_date": "Date"},
    "invoice": {"total": "Decimal", "amount": "Integer"}
}

def eval_code(code, context, explain=False):
    tokens = Lexer(code).tokenize()
    ast = Parser(tokens).parse()
    SemanticAnalyzer(SCHEMA).analyze(ast)
    return Evaluator(context, explain_mode=explain).eval_rules(ast)

def test_eval_001_basic_match():
    code = 'RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"age": 20}})
    assert decisions[0].matched == True

def test_eval_002_no_match_else():
    code = 'RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW ELSE DENY "No" END'
    decisions = eval_code(code, {"customer": {"age": 15}})
    assert decisions[0].actions[0].action_type == "DENY"

def test_eval_003_short_circuit_and():
    code = 'RULE r LANGUAGE 1 WHEN customer.active == true AND invoice.amount / 0 == 1 THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"active": False}, "invoice": {"amount": 10}})
    assert decisions[0].matched == False

def test_eval_004_short_circuit_or():
    code = 'RULE r LANGUAGE 1 WHEN customer.active == true OR invoice.amount / 0 == 1 THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"active": True}, "invoice": {"amount": 10}})
    assert decisions[0].matched == True

def test_eval_005_date_comparison():
    code = 'RULE r LANGUAGE 1 WHEN customer.birth_date > 1990-01-01 THEN ALLOW END'
    # Fix: Pasar la fecha como objeto date real, no string, para respetar el strict typing
    decisions = eval_code(code, {"customer": {"birth_date": date(1995, 5, 20)}})
    assert decisions[0].matched == True

def test_eval_006_abs_decimal():
    code = 'RULE r LANGUAGE 1 WHEN abs(invoice.total) > 50.0 THEN ALLOW END'
    decisions = eval_code(code, {"invoice": {"total": -100.5}})
    assert decisions[0].matched == True

def test_eval_007_is_null():
    code = 'RULE r LANGUAGE 1 WHEN customer.email IS NULL THEN ALERT "Missing email" END'
    decisions = eval_code(code, {"customer": {"email": None}})
    assert decisions[0].matched == True
    assert decisions[0].actions[0].action_type == "ALERT"

def test_eval_008_is_not_null():
    code = 'RULE r LANGUAGE 1 WHEN customer.email IS NOT NULL THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"email": "test@test.com"}})
    assert decisions[0].matched == True

def test_eval_009_unary_not():
    code = 'RULE r LANGUAGE 1 WHEN NOT customer.active THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"active": False}})
    assert decisions[0].matched == True

def test_eval_010_multiple_rules():
    code = """
    RULE r1 LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END
    RULE r2 LANGUAGE 1 WHEN customer.active == true THEN ALLOW END
    """
    decisions = eval_code(code, {"customer": {"age": 20, "active": True}})
    assert len(decisions) == 2
    assert decisions[0].matched == True
    assert decisions[1].matched == True

def test_eval_err_001_division_by_zero():
    code = 'RULE r LANGUAGE 1 WHEN invoice.total / 0 > 10 THEN ALLOW END'
    with pytest.raises(EvaluatorError) as exc:
        eval_code(code, {"invoice": {"total": 100.0}})
    assert exc.value.code == "RF4001"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
