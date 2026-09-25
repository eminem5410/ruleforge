import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from ruleforge import RuleForgeEngine

SCHEMA = {"customer": {"age": "Integer", "active": "Boolean", "email": "String"}}
engine = RuleForgeEngine(SCHEMA)

def get_trace(code, ctx):
    decisions = engine.evaluate(code, ctx, explain=True)
    return decisions[0].trace[0]

def test_trace_001_simple_comparison():
    code = 'RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END'
    trace = get_trace(code, {"customer": {"age": 20}})
    
    assert trace["type"] == "comparison"
    assert trace["operator"] == ">="
    assert trace["result"] is True
    
    assert trace["left"]["type"] == "property"
    assert trace["left"]["path"] == "customer.age"
    assert trace["left"]["value"] == 20
    
    assert trace["right"]["type"] == "literal"
    assert trace["right"]["value"] == 18
    assert trace["right"]["data_type"] == "Integer"

def test_trace_002_logical_and():
    code = 'RULE r LANGUAGE 1 WHEN customer.age >= 18 AND customer.active == true THEN ALLOW END'
    trace = get_trace(code, {"customer": {"age": 20, "active": True}})
    
    assert trace["type"] == "logical"
    assert trace["operator"] == "AND"
    assert trace["result"] is True
    
    # Verificar bug de booleanos arreglado (debe ser true, no "true")
    assert trace["right"]["right"]["value"] is True
    assert trace["right"]["right"]["data_type"] == "Boolean"
    assert trace["right"]["left"]["value"] is True

def test_trace_003_short_circuit_and():
    code = 'RULE r LANGUAGE 1 WHEN customer.active == false AND customer.age / 0 == 1 THEN ALLOW END'
    trace = get_trace(code, {"customer": {"active": False, "age": 20}})
    
    assert trace["type"] == "short_circuit"
    assert trace["operator"] == "AND"
    assert trace["result"] is False
    
    assert trace["left"]["left"]["value"] is False
    assert trace["left"]["right"]["value"] is False

def test_trace_004_null_check():
    code = 'RULE r LANGUAGE 1 WHEN customer.email IS NULL THEN ALLOW END'
    trace = get_trace(code, {"customer": {}})
    
    assert trace["type"] == "null_check"
    assert trace["operator"] == "IS NULL"
    assert trace["result"] is True
    
    assert trace["value"]["type"] == "property"
    assert trace["value"]["path"] == "customer.email"
    assert trace["value"]["value"] is None
