import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from ruleforge.lexer import Lexer
from ruleforge.parser import Parser
from ruleforge.semantic import SemanticAnalyzer, SemanticError
from ruleforge.evaluator import Evaluator, EvaluatorError
import ruleforge.evaluator.evaluator as eval_mod

SCHEMA = {"a": {"b": "Boolean"}}

def test_sec_ast_depth_exceeded():
    # 52 ORs encadenados = profundidad 52 (> 50)
    expr = " OR ".join(["a.b"] * 52)
    code = f'RULE r LANGUAGE 1 WHEN {expr} THEN ALLOW END'
    tokens = Lexer(code).tokenize()
    ast = Parser(tokens).parse()
    with pytest.raises(SemanticError) as exc:
        SemanticAnalyzer(SCHEMA).analyze(ast)
    assert exc.value.code == "RF5001"

def test_sec_execution_steps_exceeded():
    # En lugar de crear un AST gigante (que causa RecursionError en Python),
    # bajamos el límite de pasos del Evaluator a 3.
    code = 'RULE r LANGUAGE 1 WHEN a.b OR a.b OR a.b THEN ALLOW END'
    tokens = Lexer(code).tokenize()
    ast = Parser(tokens).parse()
    SemanticAnalyzer(SCHEMA).analyze(ast)
    
    original_limit = eval_mod.MAX_EXECUTION_STEPS
    eval_mod.MAX_EXECUTION_STEPS = 3
    
    try:
        evaluator = Evaluator({"a": {"b": False}})
        with pytest.raises(EvaluatorError) as exc:
            evaluator.eval_rules(ast)
        assert exc.value.code == "RF5003"
    finally:
        eval_mod.MAX_EXECUTION_STEPS = original_limit
