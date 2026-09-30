"""V11.3: Trace Conformance Python <-> C#.
Each vector defines a rule, context, and expected trace properties.
Both Python and C# must produce the same trace structure."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from decimal import Decimal
from datetime import date
from ruleforge import RuleEngine
from ruleforge.evaluator.evaluator import Evaluator, EvaluatorError
from ruleforge.lexer import Lexer
from ruleforge.parser import Parser
from ruleforge.semantic import SemanticAnalyzer

SCHEMA = {
    "customer": {"age": "Integer", "active": "Boolean", "email": "String",
                 "tags": "Array<String>", "birth_date": "Date", "balance": "Decimal"}
}
engine = RuleEngine(SCHEMA)

def get_trace(rule_src, ctx):
    result = engine.evaluate(rule_src, ctx, trace=True)
    return result.decisions[0].trace[0]

def get_error_trace(rule_src, ctx):
    tokens = Lexer(rule_src).tokenize()
    ast = Parser(tokens).parse()
    SemanticAnalyzer(SCHEMA).analyze(ast)
    ev = Evaluator(dict(ctx), deep_trace=True)
    try:
        ev.eval_rule(ast[0])
    except EvaluatorError:
        pass
    return ev.trace[0] if ev.trace else None

def check(trace, expected, path="root"):
    for key, exp in expected.items():
        if key == "ChildrenCount":
            actual = len(trace.get("Children", []))
            assert actual == exp, f"{path}.ChildrenCount: exp {exp}, got {actual}"
        elif key == "Children":
            kids = trace.get("Children", [])
            for i, child_exp in enumerate(exp):
                assert i < len(kids), f"{path}.Children[{i}]: missing"
                check(kids[i], child_exp, f"{path}.Children[{i}]")
        else:
            actual = trace.get(key)
            assert actual == exp, f"{path}.{key}: exp {exp!r}, got {actual!r}"

VECTORS = [
    {"id": "001", "name": "comparison", "rule": 'RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END',
     "ctx": {"customer": {"age": 20}},
     "expected": {"NodeType": "BinaryExpression", "Operator": ">=", "Value": True, "Type": "Boolean",
                  "ShortCircuited": False, "ChildrenCount": 2,
                  "Children": [{"NodeType": "PropertyExpression", "Value": 20, "Type": "Integer"},
                               {"NodeType": "Literal", "Value": 18, "Type": "Integer"}]}},

    {"id": "002", "name": "AND normal", "rule": 'RULE r LANGUAGE 1 WHEN customer.age >= 18 AND customer.active == true THEN ALLOW END',
     "ctx": {"customer": {"age": 20, "active": True}},
     "expected": {"NodeType": "BinaryExpression", "Operator": "AND", "Value": True, "ShortCircuited": False,
                  "ChildrenCount": 2,
                  "Children": [{"NodeType": "BinaryExpression", "Operator": ">="},
                               {"NodeType": "BinaryExpression", "Operator": "=="}]}},

    {"id": "003", "name": "AND short-circuit", "rule": 'RULE r LANGUAGE 1 WHEN customer.active == true AND customer.age >= 18 THEN ALLOW END',
     "ctx": {"customer": {"active": False, "age": 20}},
     "expected": {"NodeType": "BinaryExpression", "Operator": "AND", "Value": False, "ShortCircuited": False,
                  "ChildrenCount": 2,
                  "Children": [{"NodeType": "BinaryExpression", "Value": False},
                               {"NodeType": "BinaryExpression", "ShortCircuited": True, "Value": None}]}},

    {"id": "004", "name": "OR short-circuit", "rule": 'RULE r LANGUAGE 1 WHEN customer.active == true OR customer.age >= 18 THEN ALLOW END',
     "ctx": {"customer": {"active": True, "age": 20}},
     "expected": {"NodeType": "BinaryExpression", "Operator": "OR", "Value": True, "ShortCircuited": False,
                  "ChildrenCount": 2,
                  "Children": [{"NodeType": "BinaryExpression", "Value": True},
                               {"NodeType": "BinaryExpression", "ShortCircuited": True, "Value": None}]}},

    {"id": "005", "name": "NullCheck", "rule": 'RULE r LANGUAGE 1 WHEN customer.email IS NULL THEN ALLOW END',
     "ctx": {"customer": {}},
     "expected": {"NodeType": "NullCheck", "Operator": "IS NULL", "Value": True, "Type": "Boolean",
                  "ChildrenCount": 1,
                  "Children": [{"NodeType": "PropertyExpression", "Value": None}]}},

    {"id": "006", "name": "FILTER", "rule": 'RULE r LANGUAGE 2 WHEN LENGTH(FILTER customer.tags WHERE it == "vip") == 1 THEN ALLOW END',
     "ctx": {"customer": {"tags": ["admin", "vip", "user"]}},
     "expected": {"NodeType": "BinaryExpression", "Operator": "==", "Value": True,
                  "ChildrenCount": 2,
                  "Children": [{"NodeType": "FunctionCall", "ChildrenCount": 1,
                                 "Children": [{"NodeType": "FilterMap", "Operator": "FILTER", "ChildrenCount": 4}]},
                               {"NodeType": "Literal"}]}},

    {"id": "007", "name": "MAP", "rule": 'RULE r LANGUAGE 2 WHEN LENGTH(MAP customer.tags USING it) == 3 THEN ALLOW END',
     "ctx": {"customer": {"tags": ["admin", "vip", "user"]}},
     "expected": {"NodeType": "BinaryExpression", "Operator": "==", "Value": True,
                  "ChildrenCount": 2,
                  "Children": [{"NodeType": "FunctionCall", "ChildrenCount": 1,
                                 "Children": [{"NodeType": "FilterMap", "Operator": "MAP", "ChildrenCount": 4}]},
                               {"NodeType": "Literal"}]}},

    {"id": "008", "name": "ANY", "rule": 'RULE r LANGUAGE 2 WHEN ANY customer.tags WHERE it == "vip" THEN ALLOW END',
     "ctx": {"customer": {"tags": ["admin", "vip", "user"]}},
     "expected": {"NodeType": "AnyAll", "Operator": "ANY", "Value": True,
                  "ChildrenCount": 4,
                  "Children": [{"NodeType": "PropertyExpression"}, {"ShortCircuited": False},
                               {"ShortCircuited": False}, {"ShortCircuited": True, "Value": None}]}},

    {"id": "009", "name": "ALL", "rule": 'RULE r LANGUAGE 2 WHEN ALL customer.tags WHERE it == "admin" THEN ALLOW END',
     "ctx": {"customer": {"tags": ["admin", "vip", "user"]}},
     "expected": {"NodeType": "AnyAll", "Operator": "ALL", "Value": False,
                  "ChildrenCount": 4,
                  "Children": [{"NodeType": "PropertyExpression"}, {"ShortCircuited": False},
                               {"ShortCircuited": False}, {"ShortCircuited": True, "Value": None}]}},

    {"id": "010", "name": "Array literal", "rule": 'RULE r LANGUAGE 2 WHEN LENGTH([1, 2, 3]) == 3 THEN ALLOW END',
     "ctx": {},
     "expected": {"NodeType": "BinaryExpression", "Operator": "==", "Value": True,
                  "ChildrenCount": 2,
                  "Children": [{"NodeType": "FunctionCall", "ChildrenCount": 1,
                                 "Children": [{"NodeType": "ArrayLiteral", "ChildrenCount": 3}]},
                               {"NodeType": "Literal"}]}},

    {"id": "011", "name": "Array index", "rule": 'RULE r LANGUAGE 2 WHEN customer.tags[0] == "admin" THEN ALLOW END',
     "ctx": {"customer": {"tags": ["admin", "vip", "user"]}},
     "expected": {"NodeType": "BinaryExpression", "Operator": "==", "Value": True,
                  "ChildrenCount": 2,
                  "Children": [{"NodeType": "ArrayIndex"}, {"NodeType": "Literal"}]}},

    {"id": "012", "name": "Date", "rule": 'RULE r LANGUAGE 1 WHEN customer.birth_date > DATE "1990-01-01" THEN ALLOW END',
     "ctx": {"customer": {"birth_date": date(1995, 5, 20)}},
     "expected": {"NodeType": "BinaryExpression", "Operator": ">", "Value": True, "Type": "Boolean",
                  "ChildrenCount": 2,
                  "Children": [{"NodeType": "PropertyExpression", "Type": "Date", "Value": "1995-05-20"},
                               {"NodeType": "DateLiteral", "Type": "Date"}]}},

    {"id": "013", "name": "Decimal", "rule": 'RULE r LANGUAGE 1 WHEN customer.balance >= 100.50 THEN ALLOW END',
     "ctx": {"customer": {"balance": Decimal("150.75")}},
     "expected": {"NodeType": "BinaryExpression", "Operator": ">=", "Value": True, "Type": "Boolean",
                  "ChildrenCount": 2,
                  "Children": [{"NodeType": "PropertyExpression", "Type": "Decimal", "Value": "150.75"},
                               {"NodeType": "Literal", "Type": "Decimal", "Value": "100.50"}]}},

    {"id": "014", "name": "Error", "rule": 'RULE r LANGUAGE 1 WHEN customer.age / 0 > 1 THEN ALLOW END',
     "ctx": {"customer": {"age": 20}}, "is_error": True,
     "expected": {"NodeType": "BinaryExpression", "Operator": "/", "ErrorCode": "RF4001", "Value": None}},

    {"id": "015", "name": "Nested", "rule": 'RULE r LANGUAGE 1 WHEN customer.age >= 18 AND customer.active == true OR customer.email IS NULL THEN ALLOW END',
     "ctx": {"customer": {"age": 20, "active": False, "email": "test@test.com"}},
     "expected": {"NodeType": "BinaryExpression", "Operator": "OR", "Value": False, "ShortCircuited": False,
                  "ChildrenCount": 2,
                  "Children": [{"NodeType": "BinaryExpression", "Operator": "AND", "Value": False},
                               {"NodeType": "NullCheck", "Operator": "IS NULL", "Value": False}]}},

    {"id": "016", "name": "Decimal precision", "rule": 'RULE r LANGUAGE 1 WHEN customer.balance >= 1.234567890123456789 THEN ALLOW END',
     "ctx": {"customer": {"balance": Decimal("1.234567890123456789")}},
     "expected": {"NodeType": "BinaryExpression", "Operator": ">=", "Value": True, "Type": "Boolean",
                  "ChildrenCount": 2,
                  "Children": [{"NodeType": "PropertyExpression", "Type": "Decimal", "Value": "1.234567890123456789"},
                               {"NodeType": "Literal", "Type": "Decimal", "Value": "1.234567890123456789"}]}},
]

@pytest.mark.parametrize("v", VECTORS, ids=[v["id"] for v in VECTORS])
def test_trace_conformance(v):
    if v.get("is_error"):
        trace = get_error_trace(v["rule"], v["ctx"])
    else:
        trace = get_trace(v["rule"], v["ctx"])
    assert trace is not None, f"Vector {v['id']}: trace is None"
    check(trace, v["expected"])
