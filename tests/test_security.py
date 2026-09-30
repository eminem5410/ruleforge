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

def test_sec_node_count_exceeded():
    """RF5002: Wide AST (array literal with >500 elements) triggers node count.
    Before the count accumulation fix, this test would NOT trigger RF5002."""
    elements = ', '.join(str(i) for i in range(1, 503))
    code = f'RULE r LANGUAGE 2 WHEN LENGTH([{elements}]) == 502 THEN ALLOW END'
    tokens = Lexer(code).tokenize()
    ast = Parser(tokens).parse()
    with pytest.raises(SemanticError) as exc:
        SemanticAnalyzer(SCHEMA).analyze(ast)
    assert exc.value.code == "RF5002"

def test_sec_depth_anyall_where():
    """RF5001: Deep WHERE clause in ANY triggers depth limit.
    Before the AnyAll traversal fix, WHERE depth was not checked."""
    inner = 'it == "x"'
    for _ in range(49):
        inner = f'({inner} AND it == "x")'
    code = f'RULE r LANGUAGE 2 WHEN ANY customer.tags WHERE {inner} THEN ALLOW END'
    tokens = Lexer(code).tokenize()
    ast = Parser(tokens).parse()
    schema = {"customer": {"tags": "Array<String>"}}
    with pytest.raises(SemanticError) as exc:
        SemanticAnalyzer(schema).analyze(ast)
    assert exc.value.code == "RF5001"

@pytest.mark.parametrize("op,keyword,wrapper", [
    ("ANY", "WHERE", False),
    ("ALL", "WHERE", False),
    ("FILTER", "WHERE", True),
    ("MAP", "USING", True),
])
def test_sec_depth_arrayop(op, keyword, wrapper):
    """RF5001: Deep expression inside ANY/ALL/FILTER/MAP triggers depth limit."""
    needed = 49 if not wrapper else 47
    inner = 'it == "x"'
    for _ in range(needed):
        inner = f'({inner} AND it == "x")'
    if wrapper:
        code = f'RULE r LANGUAGE 2 WHEN LENGTH({op} customer.tags {keyword} {inner}) == 0 THEN ALLOW END'
    else:
        code = f'RULE r LANGUAGE 2 WHEN {op} customer.tags {keyword} {inner} THEN ALLOW END'
    tokens = Lexer(code).tokenize()
    ast = Parser(tokens).parse()
    schema = {"customer": {"tags": "Array<String>"}}
    with pytest.raises(SemanticError) as exc:
        SemanticAnalyzer(schema).analyze(ast)
    assert exc.value.code == "RF5001"

@pytest.mark.parametrize("op,keyword,wrapper", [
    ("ANY", "WHERE", False),
    ("ALL", "WHERE", False),
    ("FILTER", "WHERE", True),
    ("MAP", "USING", True),
])
def test_sec_nodecount_arrayop(op, keyword, wrapper):
    """RF5002: Large array inside ANY/ALL/FILTER/MAP triggers node count limit."""
    elements = ', '.join(str(i) for i in range(1, 503))
    if wrapper:
        code = f'RULE r LANGUAGE 2 WHEN LENGTH({op} [{elements}] {keyword} it) == 502 THEN ALLOW END'
    else:
        code = f'RULE r LANGUAGE 2 WHEN {op} [{elements}] {keyword} it THEN ALLOW END'
    tokens = Lexer(code).tokenize()
    ast = Parser(tokens).parse()
    with pytest.raises(SemanticError) as exc:
        SemanticAnalyzer(SCHEMA).analyze(ast)
    assert exc.value.code == "RF5002"

def test_sec_depth_nullcheck():
    """RF5001: Deep expression inside IS NULL triggers depth limit.
    Tests that NullCheckNode.left is traversed for depth checking."""
    inner = "customer.age"
    for _ in range(50):
        inner = f"({inner} + 1)"
    code = f'RULE r LANGUAGE 1 WHEN {inner} IS NULL THEN ALLOW END'
    tokens = Lexer(code).tokenize()
    ast = Parser(tokens).parse()
    schema = {"customer": {"age": "Integer"}}
    with pytest.raises(SemanticError) as exc:
        SemanticAnalyzer(schema).analyze(ast)
    assert exc.value.code == "RF5001"
