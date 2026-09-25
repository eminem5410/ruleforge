import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from ruleforge.lexer import Lexer
from ruleforge.parser import Parser
from ruleforge.semantic import SemanticAnalyzer
from ruleforge.evaluator import Evaluator, EvaluatorError

SCHEMA = {
    "customer": {"age": "Integer", "name": "String", "active": "Boolean", "email": "String"},
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
    assert len(decisions) == 1
    assert decisions[0].matched == True
    assert decisions[0].actions[0].action_type == "ALLOW"

def test_eval_002_no_match_else():
    code = 'RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW ELSE DENY "No" END'
    decisions = eval_code(code, {"customer": {"age": 15}})
    assert decisions[0].matched == False
    assert decisions[0].actions[0].action_type == "DENY"

def test_eval_003_explain_trace():
    code = 'RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"age": 20}}, explain=True)
    trace = decisions[0].trace
    assert len(trace) == 2
    assert "20 >= 18 -> True" in trace[0]
    assert "True" in trace[1]

def test_eval_004_function_and_logic():
    code = 'RULE r LANGUAGE 1 WHEN contains(customer.name, "Pablo") AND customer.active == true THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"name": "Pablo Diez", "active": True}})
    assert decisions[0].matched == True

def test_eval_err_001_division_by_zero():
    code = 'RULE r LANGUAGE 1 WHEN invoice.total / 0 > 10 THEN ALLOW END'
    with pytest.raises(EvaluatorError) as exc:
        eval_code(code, {"invoice": {"total": 100.0}})
    assert exc.value.code == "RF4001"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
