"""V11.4 Block 2.2: Cross-language property testing.

Invariant: for any valid rule R and context C,
    Python result == C# result

Compares: code, matched, action_type, value, payload (normalized).
Does NOT compare: error messages, trace structures, internal representations.
"""
import sys, os, json, tempfile, subprocess, copy
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from datetime import date
from decimal import Decimal
from hypothesis import given, strategies as st, settings, HealthCheck
from ruleforge import RuleEngine
from ruleforge.lexer import Lexer, LexerError
from ruleforge.parser import Parser, ParserError
from ruleforge.semantic import SemanticAnalyzer, SemanticError
from ruleforge.evaluator import EvaluatorError

SCHEMA = {
    "customer": {
        "age": "Integer",
        "active": "Boolean",
        "email": "String",
        "tags": "Array<String>",
        "birth_date": "Date",
        "risk_score": "Integer",
        "status": "String",
    },
    "invoice": {
        "total": "Decimal",
        "amount": "Decimal",
        "status": "String",
    }
}

CSHARP_RUNNER = "dotnet/src/RuleForge.ConformanceRunner/bin/Debug/net8.0/RuleForge.ConformanceRunner.dll"


def normalize(val):
    """Normalize Python values for comparison with JSON-parsed C# output."""
    if isinstance(val, Decimal):
        return format(val, "f")
    if isinstance(val, date):
        return val.isoformat()
    if isinstance(val, list):
        return [normalize(x) for x in val]
    if isinstance(val, dict):
        return {k: normalize(v) for k, v in val.items()}
    return val


def json_encode(obj):
    """JSON encoder for Decimal and date."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, date):
        return obj.isoformat()
    raise TypeError(f"Cannot serialize {type(obj)}")


def get_python_result(rule, context):
    """Evaluate rule with Python RuleEngine."""
    ctx = copy.deepcopy(context)
    try:
        engine = RuleEngine(SCHEMA)
        decisions = engine.evaluate(rule, ctx).decisions
        d = decisions[-1]
        actions = [{"action_type": a.action_type, "value": a.value, "payload": a.payload}
                   for a in d.actions]
        return {"code": None, "matched": d.matched, "actions": actions}
    except (LexerError, ParserError, SemanticError, EvaluatorError) as e:
        return {"code": e.code, "matched": False, "actions": []}


def get_csharp_result(rule, context):
    """Evaluate rule with C# ConformanceRunner via subprocess."""
    ctx = copy.deepcopy(context)
    data = {"context": ctx}
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.rf', delete=False) as rf_file:
        rf_file.write(rule)
        rf_path = rf_file.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as json_file:
        json.dump(data, json_file, default=json_encode)
        json_path = json_file.name
    
    try:
        result = subprocess.run(
            ["dotnet", CSHARP_RUNNER, rf_path, json_path],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return {"code": "CSHARP_CRASH", "matched": False, "actions": []}
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        return {"code": "CSHARP_TIMEOUT", "matched": False, "actions": []}
    finally:
        os.unlink(rf_path)
        os.unlink(json_path)


@st.composite
def cross_language_rule_and_context(draw):
    """Generate a valid RuleForge rule and matching context using only
    properties from the cross-language conformance schema."""
    age = draw(st.integers(min_value=0, max_value=120))
    active = draw(st.booleans())
    email = draw(st.one_of(
        st.none(),
        st.text(min_size=3, max_size=30,
                alphabet="abcdefghijklmnopqrstuvwxyz0123456789@.")
    ))
    tags = draw(st.lists(
        st.text(min_size=1, max_size=5, alphabet="abc"),
        min_size=0, max_size=10
    ))
    total = draw(st.decimals(min_value=0, max_value=10000,
                             allow_nan=False, allow_infinity=False, places=2))
    birth_date = draw(st.dates(min_value=date(1950, 1, 1),
                               max_value=date(2020, 12, 31)))
    risk_score = draw(st.integers(min_value=0, max_value=100))

    op = draw(st.sampled_from([">=", "<", "==", "!=", ">", "<="]))
    threshold = draw(st.integers(min_value=0, max_value=120))
    bool_val = "true" if active else "false"

    rule_type = draw(st.sampled_from([
        "age_cmp", "bool_cmp", "null_check",
        "and_combined", "or_combined",
        "error_div", "error_div_sc",
        "any", "all", "filter_len",
        "decimal_cmp", "decimal_arith",
        "date_cmp",
        "map_identity",
        "nested_and_or", "not_expr",
        "array_index", "array_index_oob",
        "error_in_any", "error_in_filter",
        "allow_action", "deny_action", "emit_action", "set_action",
    ]))

    if rule_type == "age_cmp":
        rule = f'RULE r LANGUAGE 1 WHEN customer.age {op} {threshold} THEN ALLOW END'
    elif rule_type == "bool_cmp":
        rule = f'RULE r LANGUAGE 1 WHEN customer.active == {bool_val} THEN ALLOW END'
    elif rule_type == "null_check":
        check = draw(st.sampled_from(["IS NULL", "IS NOT NULL"]))
        rule = f'RULE r LANGUAGE 1 WHEN customer.email {check} THEN ALLOW END'
    elif rule_type == "and_combined":
        rule = f'RULE r LANGUAGE 1 WHEN customer.age {op} {threshold} AND customer.active == {bool_val} THEN ALLOW END'
    elif rule_type == "or_combined":
        rule = f'RULE r LANGUAGE 1 WHEN customer.age {op} {threshold} OR customer.active == {bool_val} THEN ALLOW END'
    elif rule_type == "error_div":
        rule = f'RULE r LANGUAGE 1 WHEN customer.age / 0 > 1 THEN ALLOW END'
    elif rule_type == "error_div_sc":
        rule = f'RULE r LANGUAGE 1 WHEN customer.age < 0 AND customer.age / 0 > 1 THEN ALLOW END'
    elif rule_type == "any":
        rule = f'RULE r LANGUAGE 2 WHEN ANY customer.tags WHERE it == "a" THEN ALLOW END'
    elif rule_type == "all":
        rule = f'RULE r LANGUAGE 2 WHEN ALL customer.tags WHERE it == "a" THEN ALLOW END'
    elif rule_type == "filter_len":
        rule = f'RULE r LANGUAGE 2 WHEN LENGTH(FILTER customer.tags WHERE it == "a") == 1 THEN ALLOW END'
    elif rule_type == "decimal_cmp":
        dec_op = draw(st.sampled_from([">=", "<", "==", "!=", ">", "<="]))
        dec_threshold = draw(st.decimals(min_value=0, max_value=10000,
                                          allow_nan=False, allow_infinity=False, places=2))
        dec_str = format(dec_threshold, "f")
        rule = f'RULE r LANGUAGE 1 WHEN invoice.total {dec_op} {dec_str} THEN ALLOW END'
    elif rule_type == "decimal_arith":
        add_val = draw(st.decimals(min_value=1, max_value=100,
                                   allow_nan=False, allow_infinity=False, places=2))
        add_str = format(add_val, "f")
        target_str = format(total + add_val, "f")
        rule = f'RULE r LANGUAGE 1 WHEN invoice.total + {add_str} == {target_str} THEN ALLOW END'
    elif rule_type == "date_cmp":
        date_op = draw(st.sampled_from([">", "<", ">=", "<=", "==", "!="]))
        date_threshold = draw(st.dates(min_value=date(1950, 1, 1),
                                       max_value=date(2020, 12, 31)))
        rule = f'RULE r LANGUAGE 1 WHEN customer.birth_date {date_op} DATE "{date_threshold.isoformat()}" THEN ALLOW END'
    elif rule_type == "map_identity":
        rule = f'RULE r LANGUAGE 2 WHEN LENGTH(MAP customer.tags USING it) == {len(tags)} THEN ALLOW END'
    elif rule_type == "nested_and_or":
        rule = f'RULE r LANGUAGE 1 WHEN (customer.age {op} {threshold} AND customer.active == {bool_val}) OR customer.email IS NULL THEN ALLOW END'
    elif rule_type == "not_expr":
        rule = f'RULE r LANGUAGE 1 WHEN NOT (customer.age < {threshold}) THEN ALLOW END'
    elif rule_type == "array_index":
        if tags:
            idx = draw(st.integers(min_value=0, max_value=len(tags) - 1))
            rule = f'RULE r LANGUAGE 2 WHEN customer.tags[{idx}] == "a" THEN ALLOW END'
        else:
            rule = f'RULE r LANGUAGE 2 WHEN customer.tags[0] == "a" THEN ALLOW END'
    elif rule_type == "array_index_oob":
        rule = f'RULE r LANGUAGE 2 WHEN customer.tags[99] == "x" THEN ALLOW END'
    elif rule_type == "error_in_any":
        rule = f'RULE r LANGUAGE 2 WHEN ANY customer.tags WHERE it / 0 == 1 THEN ALLOW END'
    elif rule_type == "error_in_filter":
        rule = f'RULE r LANGUAGE 2 WHEN LENGTH(FILTER customer.tags WHERE it / 0 == 1) == 0 THEN ALLOW END'
    elif rule_type == "allow_action":
        rule = f'RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END'
    elif rule_type == "deny_action":
        rule = f'RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN DENY "blocked" END'
    elif rule_type == "emit_action":
        rule = f'RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN EMIT "adult" END'
    elif rule_type == "set_action":
        new_age = draw(st.integers(min_value=0, max_value=120))
        rule = f'RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN SET customer.age = {new_age} END'

    context = {
        "customer": {
            "age": age, "active": active, "email": email,
            "tags": tags, "birth_date": birth_date.isoformat(),
            "risk_score": risk_score, "status": "active",
        },
        "invoice": {
            "total": total,
            "amount": total,
            "status": "PENDING",
        }
    }
    return rule, context


@given(cross_language_rule_and_context())
@settings(max_examples=100, deadline=None,
          suppress_health_check=[HealthCheck.too_slow])
def test_python_equals_csharp(rule_ctx):
    """Python and C# MUST produce the same semantic result.

    Compares: code, matched, action_type, value, payload.
    Does NOT compare: error messages, trace, internal representations.

    Uses subprocess to call the C# ConformanceRunner for each example.
    """
    rule, context = rule_ctx

    py_result = get_python_result(rule, context)
    cs_result = get_csharp_result(rule, context)

    py_normalized = {
        "code": py_result["code"],
        "matched": py_result["matched"],
        "actions": [
            {
                "action_type": a["action_type"],
                "value": a["value"],
                "payload": normalize(a["payload"]),
            }
            for a in py_result["actions"]
        ]
    }

    assert py_normalized == cs_result, (
        f"Cross-language mismatch:\n"
        f"  Python: {py_normalized}\n"
        f"  C#:     {cs_result}\n"
        f"  rule: {rule}\n"
        f"  context: {context}"
    )
