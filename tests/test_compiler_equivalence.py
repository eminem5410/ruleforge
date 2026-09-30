"""V11.6 Block 1: Freeze execute() ↔ execute_single() equivalence.

Tests that both methods produce identical decisions for the same
rule and context. This is the safety net before refactoring.
"""
import sys, os, copy
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from ruleforge.lexer import Lexer
from ruleforge.parser import Parser
from ruleforge.semantic import SemanticAnalyzer
from ruleforge.compiler import RuleForgeCompiler
from ruleforge import RuleEngine

SCHEMA = {"customer": {"age": "Integer", "status": "String", "tags": "Array<String>"}}
CONTEXT = {"customer": {"age": 25, "status": "active", "tags": ["a", "b"]}}

def parse_and_compile(source, schema=SCHEMA):
    tokens = Lexer(source).tokenize()
    ast = Parser(tokens).parse()
    SemanticAnalyzer(schema).analyze(ast)
    return ast, RuleForgeCompiler(ast)

CASES = [
    ("compiled_true_allow", 'RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END', True),
    ("compiled_false_allow", 'RULE r LANGUAGE 1 WHEN customer.age >= 100 THEN ALLOW END', False),
    ("compiled_true_set", 'RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN SET customer.status = "blocked" END', True),
    ("compiled_true_emit", 'RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN EMIT "adult" END', True),
    ("compiled_false_no_else", 'RULE r LANGUAGE 1 WHEN customer.age >= 100 THEN ALLOW END', False),
    ("compiled_false_else_deny", 'RULE r LANGUAGE 1 WHEN customer.age >= 100 THEN ALLOW ELSE DENY "minor" END', False),
]

@pytest.mark.parametrize("name, source, expected_matched", CASES)
def test_execute_equals_single(name, source, expected_matched):
    """execute()[0] == execute_single(rule, ctx) for compiled rules."""
    ast, compiler = parse_and_compile(source)
    ctx = copy.deepcopy(CONTEXT)

    single = compiler.execute_single(ast[0], copy.deepcopy(ctx))
    batch = compiler.execute(copy.deepcopy(ctx))[0]

    assert single.matched == batch.matched == expected_matched
    assert len(single.actions) == len(batch.actions)
    for i, (sa, ba) in enumerate(zip(single.actions, batch.actions)):
        assert sa.action_type == ba.action_type
        assert sa.value == ba.value
        assert sa.payload == ba.payload


def test_non_compilable_fallback():
    """ANY is not compilable; both methods fall back to interpreter."""
    source = 'RULE r LANGUAGE 2 WHEN ANY customer.tags WHERE it == "a" THEN ALLOW END'
    ast, compiler = parse_and_compile(source)
    ctx = {"customer": {"tags": ["a", "b"]}}

    single = compiler.execute_single(ast[0], copy.deepcopy(ctx))
    batch = compiler.execute(copy.deepcopy(ctx))[0]

    assert single.matched == batch.matched == True
    assert single.actions[0].action_type == batch.actions[0].action_type == "ALLOW"


@st.composite
def set_chain(draw):
    """Generate N rules where each SETs a value the next reads."""
    n = draw(st.integers(min_value=2, max_value=5))
    vals = [f"step{i}" for i in range(n)]

    rules = [f'RULE r1 LANGUAGE 1 WHEN true THEN SET customer.status = "{vals[0]}" END']
    for i in range(1, n - 1):
        rules.append(f'RULE r{i+1} LANGUAGE 1 WHEN customer.status == "{vals[i-1]}" THEN SET customer.status = "{vals[i]}" END')
    rules.append(f'RULE r{n} LANGUAGE 1 WHEN customer.status == "{vals[n-2]}" THEN ALLOW END')

    return "\n".join(rules), [True] * n, vals[n - 2]


@given(set_chain())
@settings(max_examples=500, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_set_chain_interp_eq_compiler(chain):
    """SET chains: interpreter == compiler for sequential context mutation."""
    source, expected, final_val = chain

    engine_i = RuleEngine(SCHEMA, use_compiler=False)
    engine_c = RuleEngine(SCHEMA, use_compiler=True)

    ri = engine_i.evaluate(source, {"customer": {"age": 25, "status": "active"}})
    rc = engine_c.evaluate(source, {"customer": {"age": 25, "status": "active"}})

    assert len(ri.decisions) == len(rc.decisions) == len(expected)
    for i, exp in enumerate(expected):
        assert ri.decisions[i].matched == rc.decisions[i].matched == exp
    assert ri.final_context["customer"]["status"] == rc.final_context["customer"]["status"] == final_val
