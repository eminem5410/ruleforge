import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from ruleforge.lexer import Lexer
from ruleforge.parser import Parser
from ruleforge.semantic import SemanticAnalyzer, SemanticError

SCHEMA = {
    "customer": {"age": "Integer", "name": "String", "active": "Boolean", "email": "String", "birth_date": "Date"},
    "invoice": {"total": "Decimal", "due_date": "Date"}
}

def analyze_code(code):
    tokens = Lexer(code).tokenize()
    ast = Parser(tokens).parse()
    analyzer = SemanticAnalyzer(SCHEMA)
    return analyzer.analyze(ast)

def test_sem_valid_rule():
    code = """RULE r LANGUAGE 1 WHEN customer.age >= 18 AND customer.active == true THEN ALLOW END"""
    assert analyze_code(code) == True

def test_sem_err_001_type_mismatch():
    code = """RULE r LANGUAGE 1 WHEN customer.age > "65" THEN ALLOW END"""
    with pytest.raises(SemanticError) as exc:
        analyze_code(code)
    assert exc.value.code == "RF3001"
    assert "numeric" in exc.value.message

def test_sem_err_002_unknown_property():
    code = """RULE r LANGUAGE 1 WHEN customer.salary > 100 THEN ALLOW END"""
    with pytest.raises(SemanticError) as exc:
        analyze_code(code)
    assert exc.value.code == "RF3002"
    assert "salary" in exc.value.message

def test_sem_err_003_multiple_terminals():
    code = """RULE r LANGUAGE 1 WHEN true THEN ALLOW DENY "No" END"""
    with pytest.raises(SemanticError) as exc:
        analyze_code(code)
    assert exc.value.code == "RF3002"
    assert "terminal decision" in exc.value.message

def test_sem_err_004_unknown_function():
    code = """RULE r LANGUAGE 1 WHEN now() > customer.birth_date THEN ALLOW END"""
    with pytest.raises(SemanticError) as exc:
        analyze_code(code)
    assert exc.value.code == "RF3003"
    assert "now" in exc.value.message

def test_sem_err_005_when_not_boolean():
    code = """RULE r LANGUAGE 1 WHEN customer.age + 10 THEN ALLOW END"""
    with pytest.raises(SemanticError) as exc:
        analyze_code(code)
    assert exc.value.code == "RF3002"
    assert "WHEN condition" in exc.value.message

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
