import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ruleforge.lexer import Lexer, TokenType

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

def test_lex_err_001_invalid_char():
    try:
        Lexer("customer @ age").tokenize()
        assert False, "Should have raised error"
    except Exception as e:
        assert "RF1001" in str(e) and "@" in str(e)

def test_lex_err_002_unterminated_string():
    try:
        Lexer('DENY "Credit limit exceeded').tokenize()
        assert False, "Should have raised error"
    except Exception as e:
        assert "RF1001" in str(e) and "Unterminated" in str(e)

def test_lex_err_003_invalid_number():
    try:
        Lexer("invoice.total == 1.").tokenize()
        assert False, "Should have raised error"
    except Exception as e:
        assert "RF1001" in str(e) and "Invalid number" in str(e)

if __name__ == "__main__":
    test_lex_001_keyword_identifier()
    print("✅ LEX-001 PASSED")
    test_lex_002_property_access()
    print("✅ LEX-002 PASSED")
    test_lex_003_string()
    print("✅ LEX-003 PASSED")
    test_lex_004_date()
    print("✅ LEX-004 PASSED")
    test_lex_err_001_invalid_char()
    print("✅ LEX-ERR-001 PASSED")
    test_lex_err_002_unterminated_string()
    print("✅ LEX-ERR-002 PASSED")
    test_lex_err_003_invalid_number()
    print("✅ LEX-ERR-003 PASSED")
    print("\n🎉 TODOS LOS TESTS DEL LEXER PASARON!")
