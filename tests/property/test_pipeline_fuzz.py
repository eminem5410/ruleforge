"""V11.4 Block 3.3: Pipeline fuzzing.

Invariant: for any source string and context dict,
the full pipeline (Lexer -> Parser -> Semantic -> Engine)
terminates with a controlled result or RuleForge error.

Never: TypeError, IndexError, KeyError, ValueError,
RecursionError, ZeroDivisionError, or any uncontrolled exception.

Additionally: for valid rules that reach evaluation,
interpreter and compiler MUST produce identical results.
"""
import sys, os, copy
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.dirname(__file__))

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from ruleforge import RuleEngine
from ruleforge.lexer import LexerError
from ruleforge.parser import ParserError
from ruleforge.semantic import SemanticError
from ruleforge.evaluator import EvaluatorError

from test_cross_language import cross_language_rule_and_context, SCHEMA, normalize

ALLOWED = (LexerError, ParserError, SemanticError, EvaluatorError)


def run_pipeline(source, context, use_compiler=False):
    engine = RuleEngine(SCHEMA, use_compiler=use_compiler)
    ctx = copy.deepcopy(context)
    result = engine.evaluate(source, ctx)

    if not result.decisions:
        return {
            "code": None,
            "matched": None,
            "actions": [],
            "decisions": [],
        }

    d = result.decisions[-1]
    return {
        "code": None,
        "matched": d.matched,
        "actions": [(a.action_type, a.value) for a in d.actions],
        "decisions": result.decisions,
    }


# --- Test 1: Arbitrary source, simple valid context ---

@given(st.text())
@settings(max_examples=2000, deadline=None,
          suppress_health_check=[HealthCheck.too_slow])
def test_pipeline_fuzz_arbitrary_source(source):
    """Any string through the full pipeline: no uncontrolled crash."""
    ctx = {"customer": {"age": 20, "active": True}}
    try:
        run_pipeline(source, ctx)
    except ALLOWED:
        pass
    except Exception as exc:
        pytest.fail(f"Uncontrolled: {type(exc).__name__}: {exc}\nsource={source!r:.200}")


# --- Test 2: Hostile fragments + random context ---

HOSTILE_TOKENS = st.sampled_from([
    "RULE", "LANGUAGE", "1", "WHEN", "THEN", "ELSE", "END",
    "ALLOW", "DENY", "SET", "EMIT", "DATE", "ANY", "ALL",
    "FILTER", "MAP", "WHERE", "USING", "NOT", "AND", "OR",
    "IS", "NULL", "true", "false", "(", ")", "[", "]",
    ".", ",", "=", "==", "!=", ">", "<", ">=", "<=",
    "+", "-", "*", "/", '"', "\\", "0", "1", "99",
    "abc", "customer", "age", "tags", "2020-01-01",
    "9999-99-99", "//", "123abc", "1.2.3",
])


@st.composite
def hostile_source(draw):
    parts = draw(st.lists(HOSTILE_TOKENS, min_size=0, max_size=30))
    return " ".join(parts)


@st.composite
def random_context(draw):
    """Generate a context dict with random types and values."""
    age = draw(st.one_of(st.none(), st.integers(min_value=-100, max_value=200),
                         st.text(max_size=5), st.booleans()))
    active = draw(st.one_of(st.none(), st.booleans(), st.integers(min_value=0, max_value=1)))
    email = draw(st.one_of(st.none(), st.text(max_size=20)))
    tags = draw(st.one_of(
        st.none(),
        st.lists(st.text(min_size=1, max_size=5, alphabet="abc"), min_size=0, max_size=10),
        st.text(max_size=5),
    ))
    total = draw(st.one_of(st.none(), st.decimals(min_value=0, max_value=10000,
                            allow_nan=False, allow_infinity=False, places=2),
                           st.integers(min_value=0, max_value=100),
                           st.text(max_size=5)))

    return {
        "customer": {
            "age": age,
            "active": active,
            "email": email,
            "tags": tags,
            "status": "active",
            "risk_score": 50,
        },
        "invoice": {
            "total": total,
            "amount": total,
            "status": "PENDING",
        }
    }


@given(hostile_source(), random_context())
@settings(max_examples=2000, deadline=None,
          suppress_health_check=[HealthCheck.too_slow])
def test_pipeline_fuzz_hostile_with_context(source, context):
    """Hostile source + random context: no uncontrolled crash."""
    try:
        run_pipeline(source, context)
    except ALLOWED:
        pass
    except Exception as exc:
        pytest.fail(f"Uncontrolled: {type(exc).__name__}: {exc}\nsource={source!r:.200}\ncontext={context}")


# --- Test 3: Valid rules + context, interpreter ≡ compiler ---

@given(cross_language_rule_and_context())
@settings(max_examples=2000, deadline=None,
          suppress_health_check=[HealthCheck.too_slow])
def test_pipeline_interp_eq_compiler(rule_ctx):
    """Valid rules: pipeline must not crash AND interp ≡ compiler."""
    rule, context = rule_ctx

    try:
        interp = run_pipeline(rule, context, use_compiler=False)
    except ALLOWED as e_interp:
        try:
            run_pipeline(rule, context, use_compiler=True)
        except ALLOWED as e_comp:
            assert e_interp.code == e_comp.code, \
                f"Error code: interp={e_interp.code} comp={e_comp.code}\nrule={rule}"
        except Exception as exc:
            pytest.fail(f"Interp raised {e_interp.code} but comp crashed: {type(exc).__name__}\nrule={rule}")
        return
    except Exception as exc:
        pytest.fail(f"Interp uncontrolled: {type(exc).__name__}: {exc}\nrule={rule}")
        return

    try:
        comp = run_pipeline(rule, context, use_compiler=True)
    except ALLOWED as e_comp:
        pytest.fail(f"Interp OK but comp raised {e_comp.code}\nrule={rule}")
    except Exception as exc:
        pytest.fail(f"Comp uncontrolled: {type(exc).__name__}: {exc}\nrule={rule}")

    assert interp["matched"] == comp["matched"], \
        f"matched: interp={interp['matched']} comp={comp['matched']}\nrule={rule}"
    assert interp["actions"] == comp["actions"], \
        f"actions: interp={interp['actions']} comp={comp['actions']}\nrule={rule}"
