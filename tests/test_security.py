import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from ruleforge.lexer import Lexer
from ruleforge.parser import Parser
from ruleforge.semantic import SemanticAnalyzer, SemanticError
from ruleforge.evaluator import Evaluator, EvaluatorError

SCHEMA = {"a": {"b": "Boolean"}}

def test_sec_ast_depth_exceeded():
    # Crear una regla con 51 niveles de profundidad: a OR a OR ... (51 veces)
    expr = " OR ".join(["a.b"] * 52)
    code = f'RULE r LANGUAGE 1 WHEN {expr} THEN ALLOW END'
    tokens = Lexer(code).tokenize()
    ast = Parser(tokens).parse()
    with pytest.raises(SemanticError) as exc:
        SemanticAnalyzer(SCHEMA).analyze(ast)
    assert exc.value.code == "RF5001"

def test_sec_execution_steps_exceeded():
    # Crear una regla con >10000 nodos para forzar el límite de pasos
    expr = " OR ".join(["a.b"] * 5001)
    code = f'RULE r LANGUAGE 1 WHEN {expr} THEN ALLOW END'
    tokens = Lexer(code).tokenize()
    ast = Parser(tokens).parse()
    SemanticAnalyzer(SCHEMA).analyze(ast) # Esto pasa porque depth es plano (1 nivel), pero muchos nodos
    # Modificamos el límite de nodos del AST temporalmente para que pase el semántico y llegue al runtime
    import ruleforge.semantic as sem_mod
    sem_mod.MAX_AST_NODES = 20000 
    
    evaluator = Evaluator({"a": {"b": False}})
    with pytest.raises(EvaluatorError) as exc:
        evaluator.eval_rules(ast)
    assert exc.value.code == "RF5003"
