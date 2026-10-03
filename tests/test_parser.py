import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from ruleforge.parser.ast_nodes import ArrayLiteralNode, ArrayIndexNode
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

def test_parse_007_array_literal():
    code = 'RULE r LANGUAGE 2 WHEN LENGTH([1, 2, 3]) == 3 THEN ALLOW END'
    ast = parse_code(code)
    assert isinstance(ast[0].when_expr, BinaryOpNode)
    func_call = ast[0].when_expr.left
    assert isinstance(func_call, FunctionCallNode)
    assert func_call.name == "LENGTH"
    assert isinstance(func_call.args[0], ArrayLiteralNode)
    assert len(func_call.args[0].elements) == 3

def test_parse_008_array_indexing():
    code = 'RULE r LANGUAGE 2 WHEN customer.tags[0] == "admin" THEN ALLOW END'
    ast = parse_code(code)
    when = ast[0].when_expr
    assert isinstance(when, BinaryOpNode)
    # Indexing is an ArrayIndexNode
    assert isinstance(when.left, ArrayIndexNode)
    assert isinstance(when.left.array, PropertyAccessNode)
    assert when.left.index.value == "0"

def test_parse_err_003_heterogeneous_array():
    code = 'RULE r LANGUAGE 2 WHEN LENGTH([1, "hello"]) == 2 THEN ALLOW END'
    # The parser should parse this fine, the semantic analyzer will reject it later
    ast = parse_code(code)
    assert isinstance(ast[0].when_expr, BinaryOpNode)

def test_parse_err_003_language_without_version():
    """Fuzz discovery: RULE x LANGUAGE sin INTEGER → RF2002."""
    from ruleforge.lexer import Lexer
    tokens = Lexer('RULE fuzz LANGUAGE').tokenize()
    with pytest.raises(ParserError) as exc:
        Parser(tokens).parse()
    assert exc.value.code == "RF2002"

def test_parse_err_004_huge_language_version():
    """Fuzz discovery: LANGUAGE con >4300 digitos → RF2002."""
    from ruleforge.lexer import Lexer
    source = f'RULE fuzz LANGUAGE {"9"*5000} WHEN true THEN ALLOW END'
    tokens = Lexer(source).tokenize()
    with pytest.raises(ParserError) as exc:
        Parser(tokens).parse()
    assert exc.value.code == "RF2002"

def test_parse_err_005_invalid_date_literal():
    """Fuzz discovery: DATE "9999-99-99" → RF2004."""
    from ruleforge.lexer import Lexer
    tokens = Lexer('RULE r LANGUAGE 1 WHEN DATE "9999-99-99" THEN ALLOW END').tokenize()
    with pytest.raises(ParserError) as exc:
        Parser(tokens).parse()
    assert exc.value.code == "RF2004"

def test_parse_err_006_empty_token_list():
    """Fuzz discovery: Parser([]) → RF2003."""
    with pytest.raises(ParserError) as exc:
        Parser([]).parse()
    assert exc.value.code == "RF2003"

def test_parse_err_007_deep_nesting():
    """Fuzz discovery: 200 parentesis anidados → RF2004."""
    from ruleforge.lexer import Lexer
    expr = "(" * 200 + "true" + ")" * 200
    tokens = Lexer(f'RULE r LANGUAGE 1 WHEN {expr} THEN ALLOW END').tokenize()
    with pytest.raises(ParserError) as exc:
        Parser(tokens).parse()
    assert exc.value.code == "RF2004"


def test_parse_match_basic():
    """V12.0: Parser can build MatchNode AST correctly."""
    from ruleforge.lexer import Lexer
    code = 'RULE r LANGUAGE 1 MATCH customer.status CASE "ACTIVE": ALLOW DEFAULT: NO_ACTION END'
    tokens = Lexer(code).tokenize()
    ast = Parser(tokens).parse()
    
    assert len(ast) == 1
    rule = ast[0]
    assert rule.match_node is not None
    assert rule.when_expr is None
    assert rule.then_actions == []
    
    match = rule.match_node
    assert len(match.cases) == 1
    assert match.cases[0].value.value == "ACTIVE"
    assert match.cases[0].actions[0].action_type == "ALLOW"
    
    assert match.default_actions is not None
    assert match.default_actions[0].action_type == "NO_ACTION"
