import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from ruleforge import RuleForgeEngine
from ruleforge.evaluator import EvaluatorError

SCHEMA = {
    "customer": {"age": "Integer", "name": "String", "active": "Boolean"},
    "invoice": {"total": "Decimal", "paid": "Boolean"}
}
engine = RuleForgeEngine(SCHEMA)

RULE = 'RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END'

def test_runtime_valid_context():
    ctx = {"customer": {"age": 20, "name": "Pablo"}}
    decisions = engine.evaluate(RULE, ctx)
    assert decisions[0].matched == True

def test_runtime_invalid_type_string_for_int():
    ctx = {"customer": {"age": "twenty"}} # String instead of Integer
    with pytest.raises(EvaluatorError) as exc:
        engine.evaluate(RULE, ctx)
    assert exc.value.code == "RF4003"
    assert "expected Integer but got str" in exc.value.message

def test_runtime_invalid_type_bool_for_int():
    ctx = {"customer": {"age": True}} # Bool instead of Integer
    with pytest.raises(EvaluatorError) as exc:
        engine.evaluate(RULE, ctx)
    assert exc.value.code == "RF4003"

def test_runtime_invalid_structure_list_instead_of_dict():
    ctx = {"customer": ["age", 20]} # List instead of Dict
    with pytest.raises(EvaluatorError) as exc:
        engine.evaluate(RULE, ctx)
    assert exc.value.code == "RF4003"
    assert "Expected object for 'customer' but got list" in exc.value.message

def test_runtime_context_not_dict():
    ctx = [{"customer": {"age": 20}}] # Root is list instead of dict
    with pytest.raises(EvaluatorError) as exc:
        engine.evaluate(RULE, ctx)
    assert exc.value.code == "RF4003"
    assert "Expected a JSON object, but got list" in exc.value.message
