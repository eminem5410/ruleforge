import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from ruleforge.lexer import Lexer, TokenType, LexerError

def get_types(tokens):
    return [t.type for t in tokens]

def test_lex_001_keyword_identifier():
    tokens = Lexer("RULE customer_check").tokenize()
    assert get_types(tokens) == [TokenType.RULE, TokenType.IDENTIFIER, TokenType.EOF]

def test_lex_002_property_access():
    tokens = Lexer("customer.age >= 18").tokenize()
    assert get_types(tokens) == [TokenType.IDENTIFIER, TokenType.DOT, TokenType.IDENTIFIER, TokenType.GTE, TokenType.INTEGER, TokenType.EOF]

def test_lex_003_string():
    tokens = Lexer('"Credit limit exceeded"').tokenize()
    assert get_types(tokens) == [TokenType.STRING, TokenType.EOF]

def test_lex_004_date():
    tokens = Lexer("customer.birth_date == 1990-05-20").tokenize()
    assert get_types(tokens) == [TokenType.IDENTIFIER, TokenType.DOT, TokenType.IDENTIFIER, TokenType.EQ, TokenType.DATE, TokenType.EOF]

def test_lex_005_boolean_true():
    tokens = Lexer("customer.active == true").tokenize()
    assert get_types(tokens) == [TokenType.IDENTIFIER, TokenType.DOT, TokenType.IDENTIFIER, TokenType.EQ, TokenType.BOOLEAN, TokenType.EOF]

def test_lex_006_boolean_false():
    tokens = Lexer("false").tokenize()
    assert get_types(tokens) == [TokenType.BOOLEAN, TokenType.EOF]

def test_lex_007_decimal():
    tokens = Lexer("1.21").tokenize()
    assert get_types(tokens) == [TokenType.DECIMAL, TokenType.EOF]

def test_lex_008_parentheses():
    tokens = Lexer("(1 + 2)").tokenize()
    assert get_types(tokens) == [TokenType.LPAREN, TokenType.INTEGER, TokenType.PLUS, TokenType.INTEGER, TokenType.RPAREN, TokenType.EOF]

def test_lex_009_all_comparison_ops():
    tokens = Lexer("1 == 2 != 3 > 4 < 5 >= 6 <= 7").tokenize()
    assert get_types(tokens) == [TokenType.INTEGER, TokenType.EQ, TokenType.INTEGER, TokenType.NEQ, TokenType.INTEGER, TokenType.GT, TokenType.INTEGER, TokenType.LT, TokenType.INTEGER, TokenType.GTE, TokenType.INTEGER, TokenType.LTE, TokenType.INTEGER, TokenType.EOF]

def test_lex_010_comments():
    tokens = Lexer("// This is a comment\nRULE test").tokenize()
    assert get_types(tokens) == [TokenType.RULE, TokenType.IDENTIFIER, TokenType.EOF]

def test_lex_011_string_escapes():
    tokens = Lexer('"hello \\"world\\""').tokenize()
    assert tokens[0].value == 'hello "world"'
    assert tokens[0].type == TokenType.STRING

def test_lex_012_multiline_tracking():
    tokens = Lexer("RULE test\nWHEN true").tokenize()
    assert tokens[3].line == 2
    assert tokens[3].column == 1

def test_lex_err_001_invalid_char():
    with pytest.raises(LexerError) as exc:
        Lexer("customer @ age").tokenize()
    assert exc.value.code == "RF1001"
    assert "@" in exc.value.message

def test_lex_err_002_unterminated_string():
    with pytest.raises(LexerError) as exc:
        Lexer('DENY "Credit limit exceeded').tokenize()
    assert exc.value.code == "RF1001"
    assert "Unterminated" in exc.value.message

def test_lex_err_003_invalid_number():
    with pytest.raises(LexerError) as exc:
        Lexer("1.").tokenize()
    assert exc.value.code == "RF1001"
    assert "Invalid number" in exc.value.message

def test_lex_err_004_single_equal():
    with pytest.raises(LexerError) as exc:
        Lexer("= 1").tokenize()
    assert exc.value.code == "RF1001"

def test_lex_err_005_single_bang():
    with pytest.raises(LexerError) as exc:
        Lexer("! 1").tokenize()
    assert exc.value.code == "RF1001"

def test_lex_err_006_unknown_escape():
    with pytest.raises(LexerError) as exc:
        Lexer('"hello \\x"').tokenize()
    assert exc.value.code == "RF1001"
    assert "Unknown escape" in exc.value.message

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
