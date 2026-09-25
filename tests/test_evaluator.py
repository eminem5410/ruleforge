import sys
import os
from datetime import date
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from ruleforge.lexer import Lexer
from ruleforge.parser import Parser
from ruleforge.semantic import SemanticAnalyzer, SemanticError
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

# 1. PropertyAccessNode
def test_eval_001_property_access_node():
    code = 'RULE r LANGUAGE 1 WHEN customer.active == true THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"active": True}})
    assert decisions[0].matched == True

# 2. precedence completa
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
    decisions = eval_code(code, {"customer": {"age": 20}}) # No tiene 'email'
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

# 19. explain_mode / trace simple
def test_eval_019_explain_trace_simple():
    code = 'RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"age": 20}}, explain=True)
    assert "20 >= 18 -> True" in decisions[0].trace[0]

# 20. múltiples reglas
def test_eval_020_multiple_rules():
    code = """
    RULE r1 LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END
    RULE r2 LANGUAGE 1 WHEN invoice.paid == true THEN ALLOW END
    """
    decisions = eval_code(code, {"customer": {"age": 20}, "invoice": {"paid": False}})
    assert decisions[0].matched == True
    assert decisions[1].matched == False

# 21. Decision Metadata (rule_id, rule_version, language_version)
def test_eval_021_decision_metadata():
    code = 'RULE adult_check LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"age": 20}})
    assert decisions[0].rule_id == "adult_check"
    assert decisions[0].rule_version == 1
    assert decisions[0].language_version == 1

# 22. explain_mode con AND/OR
def test_eval_022_explain_trace_and_or():
    code = 'RULE r LANGUAGE 1 WHEN customer.active == true OR customer.age >= 18 THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"active": True, "age": 20}}, explain=True)
    # Como el OR hace short-circuit con True, el trace debe mostrar el short-circuit
    assert any("Short-circuit OR" in step for step in decisions[0].trace)

# 23. explain_mode con Functions
def test_eval_023_explain_trace_functions():
    code = 'RULE r LANGUAGE 1 WHEN length(customer.name) > 5 THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"name": "PabloDiez"}}, explain=True)
    assert any("Evaluando función: length" in step for step in decisions[0].trace)

# 24. Semantic Analyzer rechaza IdentifierNode suelto
def test_eval_024_identifier_node_rejected():
    code = 'RULE r LANGUAGE 1 WHEN active == true THEN ALLOW END'
    with pytest.raises(SemanticError) as exc:
        eval_code(code, {"active": True})
    assert exc.value.code == "RF3002"

# Errores runtime
def test_eval_err_001_division_by_zero():
    code = 'RULE r LANGUAGE 1 WHEN invoice.total / 0 > 10 THEN ALLOW END'
    with pytest.raises(EvaluatorError) as exc:
        eval_code(code, {"invoice": {"total": 100.0}})
    assert exc.value.code == "RF4001"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
