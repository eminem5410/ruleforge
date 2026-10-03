import pytest
from ruleforge.formatter import format_context, format_decision, format_trace, format_error

# Mocks basados en la estructura real del motor
class MockAction:
    def __init__(self, action_type, value=None):
        self.action_type = action_type
        self.value = value

class MockDecision:
    def __init__(self, rule_id, matched, actions):
        self.rule_id = rule_id
        self.matched = matched
        self.actions = actions

class MockTraceEntry:
    def __init__(self, rule_name, matched, actions, evaluation_trace):
        self.rule_name = rule_name
        self.matched = matched
        self.actions = actions
        self.evaluation_trace = evaluation_trace

def test_format_context_auto_inferred():
    res = format_context({}, None)
    assert "Schema: auto-inferred" in res

def test_format_context_explicit():
    res = format_context({}, {"fields": {}})
    assert "Schema: explicit" in res

def test_format_decision_match():
    d = MockDecision("adult", True, [MockAction("ALLOW")])
    res = format_decision(d)
    assert "✓ MATCH" in res
    assert "Rule: adult" in res
    assert "Actions: ALLOW" in res

def test_format_decision_no_match_with_deny():
    d = MockDecision("adult", False, [MockAction("DENY", "Minor")])
    res = format_decision(d)
    assert "✗ NO MATCH" in res
    assert "Actions: DENY \"Minor\"" in res

def test_format_trace_complex():
    trace_data = {
        "NodeType": "BinaryExpression",
        "Value": True,
        "Type": "Boolean",
        "Children": [
            {
                "NodeType": "PropertyExpression",
                "Value": 25,
                "Type": "Integer",
                "Children": [],
                "ShortCircuited": False
            },
            {
                "NodeType": "Literal",
                "Value": 18,
                "Type": "Integer",
                "Children": [],
                "ShortCircuited": False
            }
        ],
        "ShortCircuited": False,
        "Operator": ">="
    }
    t = MockTraceEntry("adult", True, ["ALLOW"], trace_data)
    res = format_trace(t)
    
    assert "Rule: adult" in res
    assert "BinaryExpression >=" in res
    assert "PropertyExpression -> 25" in res
    assert "Literal -> 18" in res
    assert "✓ Condition matched" in res
    assert "DECISION" in res
    assert "✓ MATCH" in res

def test_format_trace_short_circuited():
    trace_data = {
        "NodeType": "BinaryExpression",
        "Value": False,
        "Type": "Boolean",
        "Children": [
            {"NodeType": "Literal", "Value": False, "Children": [], "ShortCircuited": False},
            {"NodeType": "Literal", "Value": True, "Children": [], "ShortCircuited": True}
        ],
        "ShortCircuited": False,
        "Operator": "AND"
    }
    t = MockTraceEntry("check", False, ["DENY"], trace_data)
    res = format_trace(t)
    assert "[Short-Circuited]" in res
    assert "✗ Condition not matched" in res

def test_format_error():
    class MockError(Exception):
        pass
    err = MockError("RF4002 Runtime Error: Cannot perform '>' on NULL")
    res = format_error(err)
    assert "✗ Evaluation Error" in res
    assert "RF4002" in res
    assert "Hint: check rule syntax or schema." in res

def test_format_trace_json_array():
    # Verifica que los arrays se formateen como JSON, no como repr de Python
    trace_data = {
        "NodeType": "PropertyExpression",
        "Value": ["a", "b"],
        "Type": "Array",
        "Children": [],
        "ShortCircuited": False
    }
    t = MockTraceEntry("array_test", True, ["ALLOW"], trace_data)
    res = format_trace(t)
    
    assert 'PropertyExpression -> ["a", "b"]' in res
    assert "['a', 'b']" not in res
