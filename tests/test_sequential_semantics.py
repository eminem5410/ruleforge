"""V11.5: Sequential SET semantics regression test.

Verifies that SET from rule N is visible to rule N+1,
and that no rule can see SETs from future rules.

This test MUST pass before and after the O(N²) optimization.
Both interpreter and compiler paths are tested.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from ruleforge import RuleEngine

SCHEMA = {"customer": {"age": "Integer", "status": "String"}}

BASE_CTX = {"customer": {"age": 25, "status": "active"}}

CASES = [
    # (name, rules, expected_matched[], expected_final_status)
    ("basic_set_visible", """
RULE r1 LANGUAGE 1 WHEN true THEN SET customer.status = "blocked" END
RULE r2 LANGUAGE 1 WHEN customer.status == "blocked" THEN ALLOW END
""", [True, True], "blocked"),

    ("set_not_matching", """
RULE r1 LANGUAGE 1 WHEN true THEN SET customer.status = "blocked" END
RULE r2 LANGUAGE 1 WHEN customer.status == "active" THEN ALLOW END
""", [True, False], "blocked"),

    ("chain_3_rules", """
RULE r1 LANGUAGE 1 WHEN true THEN SET customer.status = "step1" END
RULE r2 LANGUAGE 1 WHEN customer.status == "step1" THEN SET customer.status = "step2" END
RULE r3 LANGUAGE 1 WHEN customer.status == "step2" THEN ALLOW END
""", [True, True, True], "step2"),

    ("no_future_leakage", """
RULE r1 LANGUAGE 1 WHEN customer.status == "future" THEN ALLOW END
RULE r2 LANGUAGE 1 WHEN true THEN SET customer.status = "future" END
""", [False, True], "future"),

    ("multiple_sets_last_wins", """
RULE r1 LANGUAGE 1 WHEN true THEN SET customer.status = "first" END
RULE r2 LANGUAGE 1 WHEN true THEN SET customer.status = "second" END
RULE r3 LANGUAGE 1 WHEN customer.status == "second" THEN ALLOW END
""", [True, True, True], "second"),

    ("set_then_deny", """
RULE r1 LANGUAGE 1 WHEN true THEN SET customer.status = "blocked" END
RULE r2 LANGUAGE 1 WHEN customer.status == "blocked" THEN DENY "Access denied" END
""", [True, True], "blocked"),
]


@pytest.mark.parametrize("name, rules, expected_matched, expected_status", CASES)
@pytest.mark.parametrize("use_compiler", [False, True])
def test_sequential_set(name, rules, expected_matched, expected_status, use_compiler):
    """SET from rule N visible to N+1. No future leakage."""
    engine = RuleEngine(SCHEMA, use_compiler=use_compiler)
    result = engine.evaluate(rules, {"customer": {"age": 25, "status": "active"}})

    assert len(result.decisions) == len(expected_matched), \
        f"{name}: expected {len(expected_matched)} decisions, got {len(result.decisions)}"

    for i, exp in enumerate(expected_matched):
        assert result.decisions[i].matched == exp, \
            f"{name} r{i+1} (compiler={use_compiler}): expected matched={exp}, got {result.decisions[i].matched}"

    assert result.final_context["customer"]["status"] == expected_status, \
        f"{name} (compiler={use_compiler}): expected status={expected_status}, " \
        f"got {result.final_context['customer']['status']}"
