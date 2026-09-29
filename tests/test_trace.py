import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from ruleforge import RuleEngine

SCHEMA = {"customer": {"age": "Integer", "active": "Boolean", "email": "String", "tags": "Array<String>"}}
engine = RuleEngine(SCHEMA)

def get_trace(code, ctx):
    pipeline_result = engine.evaluate(code, ctx, trace=True)
    return pipeline_result.decisions[0].trace[0]

# ===== EXISTING TESTS (UPDATED TO V11.2 FORMAT) =====

def test_trace_001_simple_comparison():
    trace = get_trace('RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END', {"customer": {"age": 20}})
    assert trace["NodeType"] == "BinaryExpression"
    assert trace["Operator"] == ">="
    assert trace["Value"] is True
    assert trace["Type"] == "Boolean"
    assert trace["ShortCircuited"] is False
    assert len(trace["Children"]) == 2
    assert trace["Children"][0]["NodeType"] == "PropertyExpression"
    assert trace["Children"][0]["Value"] == 20
    assert trace["Children"][1]["NodeType"] == "Literal"
    assert trace["Children"][1]["Value"] == 18

def test_trace_002_logical_and():
    trace = get_trace('RULE r LANGUAGE 1 WHEN customer.age >= 18 AND customer.active == true THEN ALLOW END', {"customer": {"age": 20, "active": True}})
    assert trace["NodeType"] == "BinaryExpression"
    assert trace["Operator"] == "AND"
    assert trace["Value"] is True
    assert trace["ShortCircuited"] is False
    assert len(trace["Children"]) == 2
    assert trace["Children"][0]["NodeType"] == "BinaryExpression"
    assert trace["Children"][0]["Operator"] == ">="
    assert trace["Children"][1]["NodeType"] == "BinaryExpression"
    assert trace["Children"][1]["Operator"] == "=="

def test_trace_003_short_circuit_and():
    trace = get_trace('RULE r LANGUAGE 1 WHEN customer.active == true AND customer.age >= 18 THEN ALLOW END', {"customer": {"active": False, "age": 20}})
    assert trace["NodeType"] == "BinaryExpression"
    assert trace["Operator"] == "AND"
    assert trace["Value"] is False
    assert trace["ShortCircuited"] is False
    assert len(trace["Children"]) == 2
    assert trace["Children"][0]["NodeType"] == "BinaryExpression"
    assert trace["Children"][0]["Value"] is False
    assert trace["Children"][1]["ShortCircuited"] is True
    assert trace["Children"][1]["Value"] is None
    assert trace["Children"][1]["Children"] == []

def test_trace_004_null_check():
    trace = get_trace('RULE r LANGUAGE 1 WHEN customer.email IS NULL THEN ALLOW END', {"customer": {}})
    assert trace["NodeType"] == "NullCheck"
    assert trace["Operator"] == "IS NULL"
    assert trace["Value"] is True
    assert trace["Type"] == "Boolean"
    assert len(trace["Children"]) == 1
    assert trace["Children"][0]["NodeType"] == "PropertyExpression"
    assert trace["Children"][0]["Value"] is None

# ===== NEW V11.2 TESTS =====

def test_trace_005_short_circuit_and_phantom():
    """V11.2: AND short-circuits, right child is phantom, division by zero avoided."""
    code = 'RULE r LANGUAGE 1 WHEN customer.active == true AND customer.age / 0 == 1 THEN ALLOW END'
    result = engine.evaluate(code, {"customer": {"active": False, "age": 20}}, trace=True)
    assert result.decisions[0].matched is False
    assert result.trace is not None
    root = result.trace[0].evaluation_trace
    assert root["NodeType"] == "BinaryExpression"
    assert root["Operator"] == "AND"
    assert root["Value"] is False
    assert root["ShortCircuited"] is False
    phantom = root["Children"][1]
    assert phantom["ShortCircuited"] is True
    assert phantom["Value"] is None
    assert phantom["Children"] == []

def test_trace_006_short_circuit_or_phantom():
    """V11.2: OR short-circuits, right child is phantom."""
    code = 'RULE r LANGUAGE 1 WHEN customer.active == true OR customer.age / 0 == 1 THEN ALLOW END'
    result = engine.evaluate(code, {"customer": {"active": True, "age": 20}}, trace=True)
    assert result.decisions[0].matched is True
    root = result.trace[0].evaluation_trace
    assert root["NodeType"] == "BinaryExpression"
    assert root["Operator"] == "OR"
    assert root["Value"] is True
    assert root["Children"][1]["ShortCircuited"] is True
    assert root["Children"][1]["Value"] is None

def test_trace_007_filter_trace():
    """V11.2: FILTER produces trace with array + per-item sub-expr traces."""
    code = 'RULE r LANGUAGE 2 WHEN LENGTH(FILTER customer.tags WHERE it == "vip") == 1 THEN ALLOW END'
    ctx = {"customer": {"tags": ["admin", "vip", "user"]}}
    result = engine.evaluate(code, ctx, trace=True)
    assert result.decisions[0].matched is True
    root = result.trace[0].evaluation_trace
    assert root["NodeType"] == "BinaryExpression"
    assert root["Operator"] == "=="
    length_node = root["Children"][0]
    assert length_node["NodeType"] == "FunctionCall"
    filter_node = length_node["Children"][0]
    assert filter_node["NodeType"] == "FilterMap"
    assert filter_node["Operator"] == "FILTER"
    assert isinstance(filter_node["Value"], list)
    assert len(filter_node["Value"]) == 1
    # Children: [array_trace, item1, item2, item3]
    assert len(filter_node["Children"]) == 4

def test_trace_008_any_short_circuit():
    """V11.2: ANY short-circuits on first true, remaining items are phantoms."""
    code = 'RULE r LANGUAGE 2 WHEN ANY customer.tags WHERE it == "vip" THEN ALLOW END'
    ctx = {"customer": {"tags": ["admin", "vip", "user"]}}
    result = engine.evaluate(code, ctx, trace=True)
    assert result.decisions[0].matched is True
    root = result.trace[0].evaluation_trace
    assert root["NodeType"] == "AnyAll"
    assert root["Operator"] == "ANY"
    assert root["Value"] is True
    # Children: [array_trace, item1, item2, phantom_item3]
    assert len(root["Children"]) == 4
    assert root["Children"][3]["ShortCircuited"] is True
    assert root["Children"][3]["Value"] is None
