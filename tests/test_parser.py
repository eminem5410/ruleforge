import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from ruleforge.lexer import Lexer
from ruleforge.parser import Parser, ParserError, RuleNode, ActionNode, BinaryOpNode, NullCheckNode, LiteralNode, PropertyAccessNode, FunctionCallNode

def parse_code(code):
    tokens = Lexer(code).tokenize()
    return Parser(tokens).parse()

def test_parse_001_basic_rule():
    code = """RULE test LANGUAGE 1 WHEN active == true THEN ALLOW END"""
    ast = parse_code(code)
    assert len(ast) == 1
    assert isinstance(ast[0], RuleNode)
    assert ast[0].name == "test"
    assert ast[0].lang_version == 1
    assert isinstance(ast[0].when_expr, BinaryOpNode)
    assert isinstance(ast[0].then_actions[0], ActionNode)
    assert ast[0].then_actions[0].action_type == "ALLOW"

def test_parse_002_multiple_actions():
    code = """RULE r LANGUAGE 1 WHEN true THEN DENY "No" ALERT "Check" END"""
    ast = parse_code(code)
    actions = ast[0].then_actions
    assert len(actions) == 2
    assert actions[0].action_type == "DENY"
    assert actions[0].value == "No"
    assert actions[1].action_type == "ALERT"

def test_parse_003_precedence_and_before_or():
    code = """RULE r LANGUAGE 1 WHEN a OR b AND c THEN ALLOW END"""
    ast = parse_code(code)
    when = ast[0].when_expr
    # Root should be OR
    assert when.op == "OR"
    # Right side of OR should be AND
    assert isinstance(when.right, BinaryOpNode)
    assert when.right.op == "AND"

def test_parse_err_001_missing_end():
    code = """RULE r LANGUAGE 1 WHEN true THEN ALLOW"""
    with pytest.raises(ParserError) as exc:
        parse_code(code)
    assert exc.value.code == "RF2002" # Will fail expecting END, getting EOF

def test_parse_err_002_missing_expression():
    code = """RULE r LANGUAGE 1 WHEN THEN ALLOW END"""
    with pytest.raises(ParserError) as exc:
        parse_code(code)
    assert exc.value.code in ["RF2004", "RF2002"]

def test_parse_err_003_invalid_action_mix():
    code = """RULE r LANGUAGE 1 WHEN true THEN NO_ACTION ALLOW END"""
    with pytest.raises(ParserError) as exc:
        parse_code(code)
    assert exc.value.code == "RF2005"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
