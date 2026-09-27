import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from datetime import date
from ruleforge.lexer import Lexer
from ruleforge.parser import Parser, ParserError
from ruleforge.semantic import SemanticAnalyzer
from ruleforge.evaluator import Evaluator, EvaluatorError

SCHEMA = {
    "customer": {"age": "Integer", "name": "String", "active": "Boolean", "email": "String", "tags": "Array<String>", "birth_date": "Date"},
    "invoice": {"total": "Decimal", "amount": "Integer"}
}

def eval_code(code, context, explain=False):
    tokens = Lexer(code).tokenize()
    ast = Parser(tokens).parse()
    SemanticAnalyzer(SCHEMA).analyze(ast)
    return Evaluator(context, explain_mode=explain).eval_rules(ast)

def test_eval_001_property_access_node():
    code = 'RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"age": 20}})
    assert decisions[0].matched == True

def test_eval_002_precedence():
    code = 'RULE r LANGUAGE 1 WHEN customer.age >= 18 AND customer.name == "Pablo" THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"age": 20, "name": "Pablo"}})
    assert decisions[0].matched == True

def test_eval_003_not_and_or():
    code = 'RULE r LANGUAGE 1 WHEN NOT customer.active AND customer.age > 18 OR customer.email IS NULL THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"age": 20, "active": False, "email": "test@test.com"}})
    assert decisions[0].matched == True

def test_eval_004_string_comparison():
    code = 'RULE r LANGUAGE 1 WHEN customer.name == "Pablo" THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"name": "Pablo"}})
    assert decisions[0].matched == True

def test_eval_005_date_comparison():
    code = 'RULE r LANGUAGE 1 WHEN customer.birth_date > DATE "1990-01-01" THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"birth_date": date(1995, 5, 20)}})
    assert decisions[0].matched == True

def test_eval_006_integer_math():
    code = 'RULE r LANGUAGE 1 WHEN customer.age + 10 == 30 THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"age": 20}})
    assert decisions[0].matched == True

def test_eval_007_decimal_math():
    code = 'RULE r LANGUAGE 1 WHEN invoice.total - 10.0 == 90.0 THEN ALLOW END'
    decisions = eval_code(code, {"invoice": {"total": 100.0}})
    assert decisions[0].matched == True

def test_eval_008_int_division_to_decimal():
    code = 'RULE r LANGUAGE 1 WHEN invoice.amount / 2 == 5.5 THEN ALLOW END'
    decisions = eval_code(code, {"invoice": {"amount": 11}})
    assert decisions[0].matched == True

def test_eval_009_contains():
    code = 'RULE r LANGUAGE 1 WHEN contains(customer.name, "Diez") THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"name": "Pablo Diez"}})
    assert decisions[0].matched == True

def test_eval_010_starts_with():
    code = 'RULE r LANGUAGE 1 WHEN starts_with(customer.email, "pablo") THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"email": "pablo@test.com"}})
    assert decisions[0].matched == True

def test_eval_011_ends_with():
    code = 'RULE r LANGUAGE 1 WHEN ends_with(customer.email, ".com") THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"email": "test@test.com"}})
    assert decisions[0].matched == True

def test_eval_012_length():
    code = 'RULE r LANGUAGE 1 WHEN length(customer.name) > 5 THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"name": "PabloDiez"}})
    assert decisions[0].matched == True

def test_eval_013_abs_integer():
    code = 'RULE r LANGUAGE 1 WHEN abs(customer.age) == 20 THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"age": -20}})
    assert decisions[0].matched == True

def test_eval_014_abs_decimal():
    code = 'RULE r LANGUAGE 1 WHEN abs(invoice.total) == 100.5 THEN ALLOW END'
    decisions = eval_code(code, {"invoice": {"total": -100.5}})
    assert decisions[0].matched == True

def test_eval_015_is_null_missing_property():
    code = 'RULE r LANGUAGE 1 WHEN customer.email IS NULL THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"age": 20}})
    assert decisions[0].matched == True

def test_eval_016_no_else_no_action():
    code = 'RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"age": 15}})
    assert decisions[0].matched == False
    assert decisions[0].actions[0].action_type == "NO_ACTION"

def test_eval_017_terminal_actions():
    code = 'RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN DENY "Blocked" END'
    decisions = eval_code(code, {"customer": {"age": 20}})
    assert decisions[0].actions[0].action_type == "DENY"

def test_eval_018_alert_apply():
    code = 'RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALERT "Adult" APPLY "Discount" END'
    decisions = eval_code(code, {"customer": {"age": 20}})
    assert len(decisions[0].actions) == 2

def test_eval_019_explain_trace_simple():
    code = 'RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"age": 20}}, explain=True)
    trace = decisions[0].trace[0]
    assert trace["type"] == "comparison"
    assert trace["left"]["path"] == "customer.age"
    assert trace["result"] == True

def test_eval_020_multiple_rules():
    code = """
    RULE r1 LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END
    RULE r2 LANGUAGE 1 WHEN invoice.total > 100 THEN ALLOW END
    """
    decisions = eval_code(code, {"customer": {"age": 20}, "invoice": {"total": 50.0}})
    assert decisions[0].matched == True
    assert decisions[1].matched == False

def test_eval_021_decision_metadata():
    code = 'RULE adult_check LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"age": 20}})
    assert decisions[0].rule_id == "adult_check"
    assert decisions[0].rule_version == 1
    assert decisions[0].language_version == 1

def test_eval_022_explain_trace_and_or():
    code = 'RULE r LANGUAGE 1 WHEN customer.active == true OR customer.age >= 18 THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"active": True, "age": 20}}, explain=True)
    trace = decisions[0].trace[0]
    assert trace["type"] == "short_circuit"
    assert trace["operator"] == "OR"
    assert trace["left"]["result"] == True

def test_eval_023_explain_trace_functions():
    code = 'RULE r LANGUAGE 1 WHEN length(customer.name) > 5 THEN ALLOW END'
    decisions = eval_code(code, {"customer": {"name": "PabloDiez"}}, explain=True)
    trace = decisions[0].trace[0]
    assert trace["left"]["type"] == "function"
    assert trace["left"]["name"].lower() == "length"
    assert trace["left"]["result"] == 9

def test_eval_024_identifier_node_rejected():
    code = 'RULE r LANGUAGE 1 WHEN active == true THEN ALLOW END'
    with pytest.raises(Exception):
        eval_code(code, {"active": True})

def test_eval_err_001_division_by_zero():
    code = 'RULE r LANGUAGE 1 WHEN invoice.total / 0 > 10 THEN ALLOW END'
    with pytest.raises(EvaluatorError) as exc:
        eval_code(code, {"invoice": {"total": 100.0}})
    assert exc.value.code == "RF4001"

def test_eval_025_decimal_precision():
    code = 'RULE r LANGUAGE 1 WHEN invoice.total + 0.2 == 0.3 THEN ALLOW END'
    decisions = eval_code(code, {"invoice": {"total": 0.1}})
    assert decisions[0].matched == True

def test_eval_026_null_arithmetic_error():
    code = 'RULE r LANGUAGE 1 WHEN customer.age + 10 == 30 THEN ALLOW END'
    with pytest.raises(EvaluatorError) as exc:
        eval_code(code, {"customer": {}})
    assert exc.value.code == "RF4002"

def test_eval_027_null_comparison_error():
    code = 'RULE r LANGUAGE 1 WHEN customer.age > 18 THEN ALLOW END'
    with pytest.raises(EvaluatorError) as exc:
        eval_code(code, {"customer": {}})
    assert exc.value.code == "RF4002"

def test_eval_028_null_function_error():
    code = 'RULE r LANGUAGE 1 WHEN length(customer.name) > 5 THEN ALLOW END'
    with pytest.raises(EvaluatorError) as exc:
        eval_code(code, {"customer": {}})
    assert exc.value.code == "RF4002"

# V7.0.4 Array Tests
def test_eval_029_array_literal_and_length():
    code = 'RULE r LANGUAGE 2 WHEN LENGTH([1, 2, 3]) == 3 THEN ALLOW END'
    decisions = eval_code(code, {})
    assert decisions[0].matched == True

def test_eval_030_array_indexing():
    code = 'RULE r LANGUAGE 2 WHEN customer.tags[0] == "admin" THEN ALLOW END'
    ctx = {"customer": {"tags": ["admin", "user"]}}
    decisions = eval_code(code, ctx)
    assert decisions[0].matched == True

def test_eval_err_002_array_index_out_of_bounds():
    code = 'RULE r LANGUAGE 2 WHEN customer.tags[5] == "admin" THEN ALLOW END'
    ctx = {"customer": {"tags": ["admin", "user"]}}
    with pytest.raises(EvaluatorError) as exc:
        eval_code(code, ctx)
    assert exc.value.code == "RF4002"

def test_eval_err_003_array_index_on_null():
    code = 'RULE r LANGUAGE 2 WHEN customer.tags[0] == "admin" THEN ALLOW END'
    ctx = {"customer": {}} # tags is missing -> NULL
    with pytest.raises(EvaluatorError) as exc:
        eval_code(code, ctx)
    assert exc.value.code == "RF4002"

def test_eval_031_array_contains():
    code = 'RULE r LANGUAGE 2 WHEN CONTAINS(customer.tags, "vip") THEN ALLOW END'
    ctx = {"customer": {"tags": ["standard", "vip", "beta"]}}
    decisions = eval_code(code, ctx)
    assert decisions[0].matched == True

def test_chained_array_indexing_throws_rf2004():
    rule = "RULE r LANGUAGE 1 WHEN customer.tags[0][1] == 1 THEN ALLOW END"
    tokens = Lexer(rule).tokenize()
    with pytest.raises(ParserError) as exc:
        Parser(tokens).parse()
    assert exc.value.code == "RF2004"

def test_non_literal_array_index_throws_rf2004():
    rule = "RULE r LANGUAGE 1 WHEN customer.tags[1 + 1] == 1 THEN ALLOW END"
    tokens = Lexer(rule).tokenize()
    with pytest.raises(ParserError) as exc:
        Parser(tokens).parse()
    assert exc.value.code == "RF2004"
