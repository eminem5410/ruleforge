import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from ruleforge.lexer import Lexer
from ruleforge.parser import Parser, ParserError, RuleNode, ActionNode, BinaryOpNode, UnaryOpNode, NullCheckNode, LiteralNode, IdentifierNode, PropertyAccessNode, FunctionCallNode

def parse_code(code):
    tokens = Lexer(code).tokenize()
    return Parser(tokens).parse()

def test_parse_001_basic_rule():
    code = "RULE test LANGUAGE 1 WHEN customer.active == true THEN ALLOW END"
    ast = parse_code(code)
    assert isinstance(ast[0].when_expr, BinaryOpNode)
    assert isinstance(ast[0].when_expr.left, PropertyAccessNode)

def test_parse_002_multiple_actions():
    code = 'RULE r LANGUAGE 1 WHEN true THEN DENY "No" ALERT "Check" END'
    ast = parse_code(code)
    actions = ast[0].then_actions
    assert len(actions) == 2 and actions[0].action_type == "DENY"

def test_parse_003_precedence_and_before_or():
    code = 'RULE r LANGUAGE 1 WHEN customer.a OR customer.b AND customer.c THEN ALLOW END'
    ast = parse_code(code)
    when = ast[0].when_expr
    assert when.op == "OR" and isinstance(when.right, BinaryOpNode) and when.right.op == "AND"

def test_parse_004_unary_not():
    code = 'RULE r LANGUAGE 1 WHEN NOT customer.active THEN ALLOW END'
    ast = parse_code(code)
    assert isinstance(ast[0].when_expr, UnaryOpNode)
    assert ast[0].when_expr.op == "NOT"

def test_parse_005_is_not_null():
    code = 'RULE r LANGUAGE 1 WHEN customer.email IS NOT NULL THEN ALLOW END'
    ast = parse_code(code)
    assert isinstance(ast[0].when_expr, NullCheckNode)
    assert ast[0].when_expr.is_not == True

def test_parse_006_function_call():
    code = 'RULE r LANGUAGE 1 WHEN contains(customer.name, "Pablo") THEN ALLOW END'
    ast = parse_code(code)
    assert isinstance(ast[0].when_expr, FunctionCallNode)
    assert ast[0].when_expr.name == "contains" and len(ast[0].when_expr.args) == 2

def test_parse_err_001_chained_comparison():
    code = 'RULE r LANGUAGE 1 WHEN customer.a < customer.b < customer.c THEN ALLOW END'
    with pytest.raises(ParserError) as exc:
        parse_code(code)
    assert exc.value.code == "RF2002"

def test_parse_err_002_invalid_action_mix():
    code = 'RULE r LANGUAGE 1 WHEN true THEN NO_ACTION ALLOW END'
    with pytest.raises(ParserError) as exc:
        parse_code(code)
    assert exc.value.code == "RF2005"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
