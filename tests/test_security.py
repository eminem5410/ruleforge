import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from ruleforge.lexer import Lexer
from ruleforge.parser import Parser
from ruleforge.semantic import SemanticAnalyzer, SemanticError
from ruleforge.evaluator import Evaluator, EvaluatorError
import ruleforge.semantic as sem_mod

SCHEMA = {"a": {"b": "Boolean"}}

def test_sec_ast_depth_exceeded():
    expr = " OR ".join(["a.b"] * 52)
    code = f'RULE r LANGUAGE 1 WHEN {expr} THEN ALLOW END'
    tokens = Lexer(code).tokenize()
    ast = Parser(tokens).parse()
    with pytest.raises(SemanticError) as exc:
        SemanticAnalyzer(SCHEMA).analyze(ast)
    assert exc.value.code == "RF5001"

def test_sec_execution_steps_exceeded():
    expr = " OR ".join(["a.b"] * 5001)
    code = f'RULE r LANGUAGE 1 WHEN {expr} THEN ALLOW END'
    tokens = Lexer(code).tokenize()
    ast = Parser(tokens).parse()
    
    # Aumentamos el límite de nodos del AST temporalmente para que pase el semántico
    original_limit = sem_mod.MAX_AST_NODES
    sem_mod.MAX_AST_NODES = 20000 
    
    try:
        SemanticAnalyzer(SCHEMA).analyze(ast)
        evaluator = Evaluator({"a": {"b": False}})
        with pytest.raises(EvaluatorError) as exc:
            evaluator.eval_rules(ast)
        assert exc.value.code == "RF5003"
    finally:
        # Restauramos el límite para no afectar a otros tests
        sem_mod.MAX_AST_NODES = original_limit
