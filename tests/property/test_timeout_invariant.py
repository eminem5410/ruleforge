"""V11.4 Block 3.4: No-crash / timeout invariant.

Tests that pathological inputs terminate within security limits.
RF5003 must be reachable from RuleEngine.evaluate(), not just
from Evaluator.eval_rules() directly.

Also verifies that valid but complex rules terminate with
default limits (no hangs).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import ruleforge.evaluator.evaluator as eval_mod
from ruleforge import RuleEngine
from ruleforge.evaluator import EvaluatorError

SCHEMA = {
    "customer": {"age": "Integer", "tags": "Array<String>"},
    "invoice": {"total": "Decimal"},
}


@pytest.fixture
def low_steps():
    """Temporarily set MAX_EXECUTION_STEPS=3."""
    original = eval_mod.MAX_EXECUTION_STEPS
    eval_mod.MAX_EXECUTION_STEPS = 3
    yield
    eval_mod.MAX_EXECUTION_STEPS = original


class TestRF5003FromEngine:
    """RF5003 must be reachable through RuleEngine.evaluate()."""

    def test_interpreter_or_chain(self, low_steps):
        """Interpreter: OR chain exceeds step limit via full pipeline."""
        code = 'RULE r LANGUAGE 1 WHEN customer.age >= 18 OR customer.age >= 18 OR customer.age >= 18 THEN ALLOW END'
        engine = RuleEngine(SCHEMA)
        with pytest.raises(EvaluatorError) as exc:
            engine.evaluate(code, {"customer": {"age": 20}})
        assert exc.value.code == "RF5003"

    def test_compiler_anyall_fallback(self, low_steps):
        """Compiler falls back to interpreter for ANY, triggering RF5003."""
        code = 'RULE r LANGUAGE 2 WHEN ANY customer.tags WHERE it == "a" THEN ALLOW END'
        engine = RuleEngine(SCHEMA, use_compiler=True)
        with pytest.raises(EvaluatorError) as exc:
            engine.evaluate(code, {"customer": {"tags": ["a", "b", "c"]}})
        assert exc.value.code == "RF5003"

    def test_multiple_rules(self, low_steps):
        """Multiple rules: step limit triggers across rule boundaries."""
        code = '\n'.join([
            'RULE r1 LANGUAGE 1 WHEN customer.age >= 18 OR customer.age >= 18 THEN ALLOW END',
            'RULE r2 LANGUAGE 1 WHEN customer.age >= 18 OR customer.age >= 18 THEN ALLOW END',
        ])
        engine = RuleEngine(SCHEMA)
        with pytest.raises(EvaluatorError) as exc:
            engine.evaluate(code, {"customer": {"age": 20}})
        assert exc.value.code == "RF5003"


class TestTermination:
    """Pathological but valid inputs must terminate within default limits."""

    def test_40_nested_parens(self):
        """40 nested parentheses (under depth 50): must terminate."""
        expr = "(" * 40 + "customer.age >= 18" + ")" * 40
        code = f'RULE r LANGUAGE 1 WHEN {expr} THEN ALLOW END'
        engine = RuleEngine(SCHEMA)
        result = engine.evaluate(code, {"customer": {"age": 20}})
        assert result.decisions[0].matched is True

    def test_10_compiled_rules(self):
        """10 compiled rules: must terminate without hang."""
        # V11.5: O(N^2) eliminated. execute_single() called per rule.
        # V11.6: refactored to shared _execute_compiled_rule().
        # This is a known performance issue for Block 4, not a crash.
        rules = '\n'.join([
            f'RULE r{i} LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END'
            for i in range(10)
        ])
        engine = RuleEngine(SCHEMA, use_compiler=True)
        result = engine.evaluate(rules, {"customer": {"age": 20}})
        assert len(result.decisions) == 10
        assert all(d.matched for d in result.decisions)

    def test_100_element_array_any(self):
        """ANY over 100-element array: terminates within default limit."""
        elements = ", ".join("0" for _ in range(100))
        code = f'RULE r LANGUAGE 2 WHEN ANY [{elements}] WHERE it > 0 THEN ALLOW END'
        engine = RuleEngine(SCHEMA)
        result = engine.evaluate(code, {})
        assert result.decisions[0].matched is False

    def test_100_element_filter(self):
        """FILTER 100 elements: terminates within default limit."""
        elements = ", ".join(str(i) for i in range(1, 101))
        code = f'RULE r LANGUAGE 2 WHEN LENGTH(FILTER [{elements}] WHERE it > 50) == 50 THEN ALLOW END'
        engine = RuleEngine(SCHEMA)
        result = engine.evaluate(code, {})
        assert result.decisions[0].matched is True
