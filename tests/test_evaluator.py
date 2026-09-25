import sys
import os
from datetime import date
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from ruleforge.lexer import Lexer
from ruleforge.parser import Parser
from ruleforge.semantic import SemanticAnalyzer
from ruleforge.evaluator import Evaluator, EvaluatorError

SCHEMA = {
    "customer": {"age": "Integer", "name": "String", "active": "Boolean", "email": "String", "birth_date": "Date"},
    "invoice": {"total": "Decimal", "amount": "Integer", "paid": "Boolean"}
}

def eval_code(code, context, explain=False):
    tokens = Lexer(code).tokenize()
    ast = Parser(tokens).parse()
    SemanticAnalyzer(SCHEMA).analyze(ast)
    return Evaluator(context, explain_mode=explain).eval_rules(ast)

# 1. IdentifierNode
def test_eval_001_identifier_node():
    code = 'RULE r LANGUAGE 1 WHEN customer.active == true THEN ALLOW END'
    # 'customer.active' usa PropertyAccessNode, pero si fuera 'active' suelto sería IdentifierNode
    decisions = eval_code(code, {"customer": {"active": True}})
    assert decisions[0].matched == True

# 2. precedence completa (AND antes que OR)
def test_eval_002_precedence():
    code = 'RULE r LANGUAGE 1 WHEN customer.active == false OR customer.age >= 18 AND customer.age <= 65 THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"active": False, "age": 20}})
    assert decisions[0].matched == True

# 3. NOT + AND + OR
def test_eval_003_not_and_or():
    code = 'RULE r LANGUAGE 1 WHEN NOT customer.active AND customer.age > 18 OR customer.email IS NULL THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"active": False, "age": 20, "email": "test@test.com"}})
    assert decisions[0].matched == True

# 4. comparación String
def test_eval_004_string_comparison():
    code = 'RULE r LANGUAGE 1 WHEN customer.name == "Pablo" THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"name": "Pablo"}})
    assert decisions[0].matched == True

# 5. comparación Date
def test_eval_005_date_comparison():
    code = 'RULE r LANGUAGE 1 WHEN customer.birth_date > 1990-01-01 THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"birth_date": date(1995, 5, 20)}})
    assert decisions[0].matched == True

# 6. operaciones Integer
def test_eval_006_integer_math():
    code = 'RULE r LANGUAGE 1 WHEN customer.age + 10 == 30 THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"age": 20}})
    assert decisions[0].matched == True

# 7. operaciones Decimal
def test_eval_007_decimal_math():
    code = 'RULE r LANGUAGE 1 WHEN invoice.total - 10.0 == 90.0 THEN ALLOW END'
    decisions = eval_code(code, {"invoice": {"total": 100.0}})
    assert decisions[0].matched == True

# 8. Integer / Integer → Decimal
def test_eval_008_int_division_to_decimal():
    code = 'RULE r LANGUAGE 1 WHEN invoice.amount / 2 == 5.5 THEN ALLOW END'
    decisions = eval_code(code, {"invoice": {"amount": 11}})
    assert decisions[0].matched == True

# 9. contains()
def test_eval_009_contains():
    code = 'RULE r LANGUAGE 1 WHEN contains(customer.name, "Diez") THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"name": "Pablo Diez"}})
    assert decisions[0].matched == True

# 10. starts_with()
def test_eval_010_starts_with():
    code = 'RULE r LANGUAGE 1 WHEN starts_with(customer.email, "pablo") THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"email": "pablo@test.com"}})
    assert decisions[0].matched == True

# 11. ends_with()
def test_eval_011_ends_with():
    code = 'RULE r LANGUAGE 1 WHEN ends_with(customer.email, ".com") THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"email": "test@test.com"}})
    assert decisions[0].matched == True

# 12. length()
def test_eval_012_length():
    code = 'RULE r LANGUAGE 1 WHEN length(customer.name) > 5 THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"name": "PabloDiez"}})
    assert decisions[0].matched == True

# 13. abs(Integer)
def test_eval_013_abs_integer():
    code = 'RULE r LANGUAGE 1 WHEN abs(customer.age) == 20 THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"age": -20}})
    assert decisions[0].matched == True

# 14. abs(Decimal)
def test_eval_014_abs_decimal():
    code = 'RULE r LANGUAGE 1 WHEN abs(invoice.total) == 100.5 THEN ALLOW END'
    decisions = eval_code(code, {"invoice": {"total": -100.5}})
    assert decisions[0].matched == True

# 15. IS NULL sobre propiedad inexistente en el contexto
def test_eval_015_is_null_missing_property():
    code = 'RULE r LANGUAGE 1 WHEN customer.email IS NULL THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"age": 20}}) # No tiene 'email' en el contexto
    assert decisions[0].matched == True

# 16. ELSE ausente → NO_ACTION
def test_eval_016_no_else_no_action():
    code = 'RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"age": 15}})
    assert decisions[0].matched == False
    assert decisions[0].actions[0].action_type == "NO_ACTION"

# 17. terminal actions
def test_eval_017_terminal_actions():
    code = 'RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN DENY "Blocked" END'
    decisions = eval_code(code, {"customer": {"age": 20}})
    assert decisions[0].actions[0].action_type == "DENY"

# 18. ALERT / APPLY
def test_eval_018_alert_apply():
    code = 'RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALERT "Adult" APPLY "Discount" END'
    decisions = eval_code(code, {"customer": {"age": 20}})
    assert len(decisions[0].actions) == 2
    assert decisions[0].actions[0].action_type == "ALERT"
    assert decisions[0].actions[1].action_type == "APPLY"

# 19. explain_mode / trace
def test_eval_019_explain_trace():
    code = 'RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"age": 20}}, explain=True)
    assert len(decisions[0].trace) == 2
    assert "20 >= 18 -> True" in decisions[0].trace[0]

# 20. múltiples reglas con contextos distintos (el contexto cambia entre reglas)
def test_eval_020_multiple_rules():
    code = """
    RULE r1 LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END
    RULE r2 LANGUAGE 1 WHEN invoice.paid == true THEN ALLOW END
    """
    decisions = eval_code(code, {"customer": {"age": 20}, "invoice": {"paid": False}})
    assert decisions[0].matched == True
    assert decisions[1].matched == False

# Errores runtime
def test_eval_err_001_division_by_zero():
    code = 'RULE r LANGUAGE 1 WHEN invoice.total / 0 > 10 THEN ALLOW END'
    with pytest.raises(EvaluatorError) as exc:
        eval_code(code, {"invoice": {"total": 100.0}})
    assert exc.value.code == "RF4001"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
