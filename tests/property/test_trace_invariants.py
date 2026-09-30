"""V11.4 Block 2.1: Property-based testing for trace invariant.

Invariant: for any valid rule R and context C,
    evaluate(R, C, trace=False) == evaluate(R, C, trace=True)

Covers: integers, decimals, dates, booleans, null checks,
AND/OR short-circuit, NOT, nested expressions, ANY/ALL/FILTER/MAP,
array indexing, errors inside collections, SET/EMIT actions.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from datetime import date
from hypothesis import given, strategies as st, settings, HealthCheck
from ruleforge import RuleEngine
from ruleforge.evaluator.evaluator import EvaluatorError

SCHEMA = {
    "customer": {
        "age": "Integer",
        "active": "Boolean",
        "email": "String",
        "tags": "Array<String>",
        "numbers": "Array<Integer>",
        "balance": "Decimal",
        "birth_date": "Date",
    }
}
engine = RuleEngine(SCHEMA)


@st.composite
def rule_and_context(draw):
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
    numbers = draw(st.lists(
        st.integers(min_value=-10, max_value=10),
        min_size=0, max_size=10
    ))
    balance = draw(st.decimals(min_value=0, max_value=10000,
                             allow_nan=False, allow_infinity=False, places=2))
    birth_date = draw(st.dates(min_value=date(1950, 1, 1),
                               max_value=date(2020, 12, 31)))

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
        "set_action", "emit_action",
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
        dec_threshold_str = f'{dec_threshold:.2f}'
        rule = f'RULE r LANGUAGE 1 WHEN customer.balance {dec_op} {dec_threshold_str} THEN ALLOW END'
    elif rule_type == "decimal_arith":
        add_val = draw(st.decimals(min_value=1, max_value=100,
                                 allow_nan=False, allow_infinity=False, places=2))
        add_str = f'{add_val:.2f}'
        target_str = f'{balance + add_val:.2f}'
        rule = f'RULE r LANGUAGE 1 WHEN customer.balance + {add_str} == {target_str} THEN ALLOW END'
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
        rule = f'RULE r LANGUAGE 2 WHEN ANY customer.numbers WHERE it / 0 == 1 THEN ALLOW END'
    elif rule_type == "error_in_filter":
        rule = f'RULE r LANGUAGE 2 WHEN LENGTH(FILTER customer.numbers WHERE it / 0 == 1) == 0 THEN ALLOW END'
    elif rule_type == "set_action":
        new_age = draw(st.integers(min_value=0, max_value=120))
        rule = f'RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN SET customer.age = {new_age} END'
    elif rule_type == "emit_action":
        rule = f'RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN EMIT "adult" END'

    context = {
        "customer": {
            "age": age, "active": active, "email": email,
            "tags": tags, "numbers": numbers, "balance": balance,
            "birth_date": birth_date.isoformat(),
        }
    }
    return rule, context


def extract_decision(result):
    """Extract comparable representation: matched + action types + payloads."""
    if not result.decisions:
        return ("no_decision",)
    d = result.decisions[0]
    actions = []
    for a in d.actions:
        if a.action_type == "SET":
            actions.append(("SET", a.value, repr(a.payload)))
        elif a.action_type == "EMIT":
            actions.append(("EMIT", a.value, repr(a.payload)))
        else:
            actions.append((a.action_type,))
    return ("matched", d.matched, tuple(actions))


@given(rule_and_context())
@settings(max_examples=1000, deadline=None,
          suppress_health_check=[HealthCheck.too_slow])
def test_trace_invariant(rule_ctx):
    """trace=False and trace=True MUST produce the same semantic result.

    Verifies the V11.3 Golden Rule: trace is observability, not semantics.
    Covers 22 rule families including errors, collections, and actions.
    """
    rule, context = rule_ctx

    try:
        result_false = engine.evaluate(rule, context, trace=False)
    except EvaluatorError as e_false:
        with pytest.raises(EvaluatorError) as exc_info:
            engine.evaluate(rule, context, trace=True)
        assert exc_info.value.code == e_false.code, \
            f"Error code mismatch:\n  trace=False: {e_false.code}\n  trace=True:  {exc_info.value.code}\n  rule: {rule}"
        return

    try:
        result_true = engine.evaluate(rule, context, trace=True)
    except EvaluatorError as e_true:
        pytest.fail(
            f"trace=False succeeded but trace=True raised {e_true.code}\n"
            f"  rule: {rule}\n  context: {context}"
        )

    decision_false = extract_decision(result_false)
    decision_true = extract_decision(result_true)

    assert decision_false == decision_true, (
        f"Decision mismatch:\n"
        f"  trace=False: {decision_false}\n"
        f"  trace=True:  {decision_true}\n"
        f"  rule: {rule}\n  context: {context}"
    )
