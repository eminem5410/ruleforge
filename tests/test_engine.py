import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from ruleforge import RuleForgeEngine
from ruleforge.lexer import LexerError
from ruleforge.parser import ParserError
from ruleforge.semantic import SemanticError
from ruleforge.evaluator import EvaluatorError

SCHEMA = {"customer": {"age": "Integer", "active": "Boolean"}}
engine = RuleForgeEngine(SCHEMA)

def test_engine_valid():
    code = 'RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END'
    ctx = {"customer": {"age": 20}}
    decisions = engine.evaluate(code, ctx)
    assert decisions[0].matched == True

def test_engine_semantic_error():
    code = 'RULE r LANGUAGE 1 WHEN customer.age > "18" THEN ALLOW END'
    ctx = {"customer": {"age": 20}}
    with pytest.raises(SemanticError):
        engine.evaluate(code, ctx)

def test_engine_parser_error():
    code = 'RULE r LANGUAGE 1 WHEN customer.age > 18 THEN ALLOW'
    ctx = {"customer": {"age": 20}}
    with pytest.raises(ParserError):
        engine.evaluate(code, ctx)

def test_engine_lexer_error():
    code = 'RULE r LANGUAGE 1 WHEN customer.age @> 18 THEN ALLOW END'
    ctx = {"customer": {"age": 20}}
    with pytest.raises(LexerError):
        engine.evaluate(code, ctx)

def test_engine_explain_mode():
    code = 'RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END'
    ctx = {"customer": {"age": 20}}
    decisions = engine.evaluate(code, ctx, explain=True)
    assert len(decisions[0].trace) > 0
