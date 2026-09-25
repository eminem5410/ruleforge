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
    ctx = {"customer": {"age": "twenty"}}
    with pytest.raises(EvaluatorError) as exc:
        engine.evaluate(RULE, ctx)
    assert exc.value.code == "RF4003"
    assert "expected Integer but got str" in exc.value.message

def test_runtime_invalid_type_bool_for_int():
    ctx = {"customer": {"age": True}}
    with pytest.raises(EvaluatorError) as exc:
        engine.evaluate(RULE, ctx)
    assert exc.value.code == "RF4003"

def test_runtime_invalid_structure_list_instead_of_dict():
    ctx = {"customer": ["age", 20]}
    with pytest.raises(EvaluatorError) as exc:
        engine.evaluate(RULE, ctx)
    assert exc.value.code == "RF4003"
    assert "Expected object for 'customer' but got list" in exc.value.message

def test_runtime_context_not_dict():
    ctx = [{"customer": {"age": 20}}]
    with pytest.raises(EvaluatorError) as exc:
        engine.evaluate(RULE, ctx)
    assert exc.value.code == "RF4003"
    assert "Expected a JSON object, but got list" in exc.value.message

# Tests adicionales (Decimal, Date, Boolean, Missing)

SCHEMA_FULL = {
    "customer": {"age": "Integer", "balance": "Decimal", "active": "Boolean", "birth_date": "Date"}
}
engine_full = RuleForgeEngine(SCHEMA_FULL)

def test_runtime_valid_decimal():
    ctx = {"customer": {"balance": 150.75}}
    rule = 'RULE r LANGUAGE 1 WHEN customer.balance > 100.0 THEN ALLOW END'
    decisions = engine_full.evaluate(rule, ctx)
    assert decisions[0].matched == True

def test_runtime_invalid_decimal_with_string():
    ctx = {"customer": {"balance": "150.75"}}
    rule = 'RULE r LANGUAGE 1 WHEN customer.balance > 100.0 THEN ALLOW END'
    with pytest.raises(EvaluatorError) as exc:
        engine_full.evaluate(rule, ctx)
    assert exc.value.code == "RF4003"
    assert "expected Decimal but got str" in exc.value.message

def test_runtime_valid_date():
    ctx = {"customer": {"birth_date": "1990-05-20"}}
    rule = 'RULE r LANGUAGE 1 WHEN customer.birth_date > 1990-01-01 THEN ALLOW END'
    decisions = engine_full.evaluate(rule, ctx)
    assert decisions[0].matched == True

def test_runtime_invalid_date_with_int():
    ctx = {"customer": {"birth_date": 12345}}
    rule = 'RULE r LANGUAGE 1 WHEN customer.birth_date > 1990-01-01 THEN ALLOW END'
    with pytest.raises(EvaluatorError) as exc:
        engine_full.evaluate(rule, ctx)
    assert exc.value.code == "RF4003"
    assert "expected Date but got int" in exc.value.message

def test_runtime_valid_boolean():
    ctx = {"customer": {"active": True}}
    rule = 'RULE r LANGUAGE 1 WHEN customer.active == true THEN ALLOW END'
    decisions = engine_full.evaluate(rule, ctx)
    assert decisions[0].matched == True

def test_runtime_missing_property_allowed_as_null():
    # Propiedad 'balance' falta en el contexto -> tratada como NULL -> IS NULL da True
    ctx = {"customer": {"age": 20}} 
    rule = 'RULE r LANGUAGE 1 WHEN customer.balance IS NULL THEN ALLOW END'
    decisions = engine_full.evaluate(rule, ctx)
    assert decisions[0].matched == True

def test_runtime_missing_object_allowed_as_null():
    # Objeto 'invoice' no está en SCHEMA_FULL, pero 'customer.email' tampoco, 
    # así que probamos con una propiedad que sí está en el schema pero falta en el ctx.
    # Mejor: usamos el SCHEMA original que tiene 'invoice'.
    rule = 'RULE r LANGUAGE 1 WHEN invoice.total IS NULL THEN ALLOW END'
    ctx = {"customer": {"age": 20}}
    decisions = engine.evaluate(rule, ctx)
    assert decisions[0].matched == True
