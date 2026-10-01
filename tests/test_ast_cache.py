"""V11.7: AST Cache regression tests.

Verifies that cached evaluations produce identical results to
non-cached evaluations, and that cache state does not leak
between calls with different contexts or schemas.
"""
import sys, os, copy
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from decimal import Decimal
from ruleforge import RuleEngine

SCHEMA = {
    "customer": {"age": "Integer", "status": "String"},
    "invoice": {"total": "Decimal", "status": "String"},
}

RULE_SIMPLE = 'RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END'
RULE_SET = """
RULE r1 LANGUAGE 1 WHEN true THEN SET customer.status = "blocked" END
RULE r2 LANGUAGE 1 WHEN customer.status == "blocked" THEN ALLOW END
"""
RULE_COMPLEX = 'RULE r LANGUAGE 1 WHEN (customer.age >= 18 AND invoice.total > 100) OR customer.status == "vip" THEN ALLOW END'


class TestCacheEquivalence:
    """Cached results must equal non-cached results."""

    def test_simple_cached_equals_uncached(self):
        engine = RuleEngine(SCHEMA)
        ctx = {"customer": {"age": 25, "status": "active"},
               "invoice": {"total": Decimal("50"), "status": "PENDING"}}
        # First call (cache miss)
        r1 = engine.evaluate(RULE_SIMPLE, copy.deepcopy(ctx))
        # Second call (cache hit, same source)
        r2 = engine.evaluate(RULE_SIMPLE, copy.deepcopy(ctx))
        assert r1.decisions[0].matched == r2.decisions[0].matched
        assert r1.final_context == r2.final_context

    def test_complex_cached_equals_uncached(self):
        engine = RuleEngine(SCHEMA)
        ctx1 = {"customer": {"age": 25, "status": "vip"},
                "invoice": {"total": Decimal("50"), "status": "PENDING"}}
        ctx2 = {"customer": {"age": 15, "status": "regular"},
                "invoice": {"total": Decimal("200"), "status": "PENDING"}}

        r1 = engine.evaluate(RULE_COMPLEX, copy.deepcopy(ctx1))
        r2 = engine.evaluate(RULE_COMPLEX, copy.deepcopy(ctx1))
        ctx3 = {"customer": {"age": 15, "status": "regular"},
                "invoice": {"total": Decimal("50"), "status": "PENDING"}}
        r3 = engine.evaluate(RULE_COMPLEX, copy.deepcopy(ctx3))

        assert r1.decisions[0].matched is True   # vip
        assert r2.decisions[0].matched is True   # cache hit, same result
        assert r3.decisions[0].matched is False  # 15<18, 50<100, not vip

    def test_set_sequential_with_cache(self):
        """SET semantics preserved across cache hits."""
        engine = RuleEngine(SCHEMA)
        ctx = {"customer": {"age": 25, "status": "active"},
               "invoice": {"total": Decimal("100"), "status": "PENDING"}}

        # First call: cache miss, SET applies
        r1 = engine.evaluate(RULE_SET, copy.deepcopy(ctx))
        assert r1.decisions[0].matched is True
        assert r1.decisions[1].matched is True
        assert r1.final_context["customer"]["status"] == "blocked"

        # Second call: cache hit, same result with fresh context
        r2 = engine.evaluate(RULE_SET, copy.deepcopy(ctx))
        assert r2.decisions[0].matched is True
        assert r2.decisions[1].matched is True
        assert r2.final_context["customer"]["status"] == "blocked"

        # Third call: cache hit, different context
        ctx2 = {"customer": {"age": 15, "status": "active"},
                "invoice": {"total": Decimal("100"), "status": "PENDING"}}
        r3 = engine.evaluate(RULE_SET, copy.deepcopy(ctx2))
        assert r3.decisions[0].matched is True  # rule 1 always matches
        assert r3.decisions[1].matched is True  # rule 2 sees SET from rule 1
        assert r3.final_context["customer"]["status"] == "blocked"


class TestCacheIsolation:
    """Cache must not leak state between calls."""

    def test_different_contexts_same_rule(self):
        """Same rule source, different contexts: independent results."""
        engine = RuleEngine(SCHEMA)
        ctx_young = {"customer": {"age": 15, "status": "active"},
                     "invoice": {"total": Decimal("100"), "status": "PENDING"}}
        ctx_old = {"customer": {"age": 25, "status": "active"},
                   "invoice": {"total": Decimal("100"), "status": "PENDING"}}

        r1 = engine.evaluate(RULE_SIMPLE, copy.deepcopy(ctx_young))
        r2 = engine.evaluate(RULE_SIMPLE, copy.deepcopy(ctx_old))

        assert r1.decisions[0].matched is False  # 15 < 18
        assert r2.decisions[0].matched is True   # 25 >= 18

    def test_different_schemas_same_rule(self):
        """Same rule source, different schemas: independent analysis."""
        schema_a = {"customer": {"age": "Integer"}}
        schema_b = {"customer": {"age": "String"}}  # wrong type for >=

        engine_a = RuleEngine(schema_a)
        engine_b = RuleEngine(schema_b)

        r_a = engine_a.evaluate(RULE_SIMPLE, {"customer": {"age": 25}})
        assert r_a.decisions[0].matched is True

        with pytest.raises(Exception):
            engine_b.evaluate(RULE_SIMPLE, {"customer": {"age": "hello"}})

    def test_set_does_not_leak_to_next_call(self):
        """SET from one evaluation must not affect the next."""
        engine = RuleEngine(SCHEMA)
        ctx = {"customer": {"age": 25, "status": "active"},
               "invoice": {"total": Decimal("100"), "status": "PENDING"}}

        # First call: SET status to "blocked"
        r1 = engine.evaluate(RULE_SET, copy.deepcopy(ctx))
        assert r1.final_context["customer"]["status"] == "blocked"

        # Second call: fresh context, status still "active"
        r2 = engine.evaluate(RULE_SET, copy.deepcopy(ctx))
        assert r2.final_context["customer"]["status"] == "blocked"
        # The original ctx must not be mutated
        assert ctx["customer"]["status"] == "active"

    def test_invalid_rule_does_not_pollute_cache(self):
        """A semantic error must not store anything in cache."""
        engine = RuleEngine(SCHEMA)
        bad_rule = 'RULE r LANGUAGE 1 WHEN customer.nonexistent >= 18 THEN ALLOW END'

        with pytest.raises(Exception):
            engine.evaluate(bad_rule, {"customer": {"age": 25}})

        # Cache should not contain the bad rule
        good_rule = 'RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END'
        r = engine.evaluate(good_rule, {"customer": {"age": 25}})
        assert r.decisions[0].matched is True


class TestCacheLRU:
    """LRU eviction behavior."""

    def test_cache_limit_eviction(self):
        """Cache evicts oldest entries when limit reached."""
        engine = RuleEngine({"customer": {"age": "Integer"}}, max_cache_size=3)

        # Fill cache with 3 different rules
        engine.evaluate('RULE r1 LANGUAGE 1 WHEN customer.age >= 10 THEN ALLOW END',
                        {"customer": {"age": 20}})
        engine.evaluate('RULE r2 LANGUAGE 1 WHEN customer.age >= 20 THEN ALLOW END',
                        {"customer": {"age": 20}})
        engine.evaluate('RULE r3 LANGUAGE 1 WHEN customer.age >= 30 THEN ALLOW END',
                        {"customer": {"age": 20}})

        # 4th rule should evict r1
        engine.evaluate('RULE r4 LANGUAGE 1 WHEN customer.age >= 40 THEN ALLOW END',
                        {"customer": {"age": 20}})

        # r1 should be a cache miss (re-parsed)
        # r2, r3, r4 should be cache hits
        # We verify by checking results are still correct
        r1 = engine.evaluate('RULE r1 LANGUAGE 1 WHEN customer.age >= 10 THEN ALLOW END',
                              {"customer": {"age": 20}})
        assert r1.decisions[0].matched is True

    def test_cache_disabled_when_size_zero(self):
        """max_cache_size=0 disables caching entirely."""
        engine = RuleEngine(SCHEMA, max_cache_size=0)
        ctx = {"customer": {"age": 25, "status": "active"},
               "invoice": {"total": Decimal("100"), "status": "PENDING"}}

        r1 = engine.evaluate(RULE_SIMPLE, copy.deepcopy(ctx))
        r2 = engine.evaluate(RULE_SIMPLE, copy.deepcopy(ctx))
        assert r1.decisions[0].matched == r2.decisions[0].matched


class TestCacheExplainTrace:
    """explain/trace must work correctly with cache."""

    def test_explain_cold_warm(self):
        engine = RuleEngine(SCHEMA)
        ctx = {"customer": {"age": 25, "status": "active"},
               "invoice": {"total": Decimal("100"), "status": "PENDING"}}

        r1 = engine.evaluate(RULE_SIMPLE, copy.deepcopy(ctx), explain=True)
        r2 = engine.evaluate(RULE_SIMPLE, copy.deepcopy(ctx), explain=True)

        assert r1.decisions[0].matched == r2.decisions[0].matched
        assert len(r1.decisions[0].trace) > 0
        assert len(r2.decisions[0].trace) > 0

    def test_trace_cold_warm(self):
        engine = RuleEngine(SCHEMA)
        ctx = {"customer": {"age": 25, "status": "active"},
               "invoice": {"total": Decimal("100"), "status": "PENDING"}}

        r1 = engine.evaluate(RULE_SIMPLE, copy.deepcopy(ctx), trace=True)
        r2 = engine.evaluate(RULE_SIMPLE, copy.deepcopy(ctx), trace=True)

        assert r1.trace is not None
        assert r2.trace is not None

    def test_compiler_cold_warm(self):
        engine = RuleEngine(SCHEMA, use_compiler=True)
        ctx = {"customer": {"age": 25, "status": "active"},
               "invoice": {"total": Decimal("100"), "status": "PENDING"}}

        r1 = engine.evaluate(RULE_SIMPLE, copy.deepcopy(ctx))
        r2 = engine.evaluate(RULE_SIMPLE, copy.deepcopy(ctx))

        assert r1.decisions[0].matched == r2.decisions[0].matched


class TestCacheStats:
    """Cache statistics observability."""

    def test_hits_misses_counted(self):
        engine = RuleEngine({"customer": {"age": "Integer"}})
        rule = 'RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END'
        ctx = {"customer": {"age": 25}}

        engine.evaluate(rule, copy.deepcopy(ctx))
        engine.evaluate(rule, copy.deepcopy(ctx))
        engine.evaluate(rule, copy.deepcopy(ctx))

        assert engine._cache_hits == 2
        assert engine._cache_misses == 1

    def test_lru_real_eviction(self):
        engine = RuleEngine({"customer": {"age": "Integer"}}, max_cache_size=2)
        ctx = {"customer": {"age": 25}}

        r1 = 'RULE r1 LANGUAGE 1 WHEN customer.age >= 10 THEN ALLOW END'
        r2 = 'RULE r2 LANGUAGE 1 WHEN customer.age >= 20 THEN ALLOW END'
        r3 = 'RULE r3 LANGUAGE 1 WHEN customer.age >= 30 THEN ALLOW END'

        engine.evaluate(r1, copy.deepcopy(ctx))
        engine.evaluate(r2, copy.deepcopy(ctx))
        engine.evaluate(r2, copy.deepcopy(ctx))  # hit, r2 most recent
        engine.evaluate(r3, copy.deepcopy(ctx))  # miss, evicts r1

        assert engine._cache_hits == 1
        assert engine._cache_misses == 3

        # r1 was evicted: accessing it should be a miss
        engine.evaluate(r1, copy.deepcopy(ctx))
        assert engine._cache_misses == 4

    def test_nested_schema_deterministic(self):
        schema = {"customer": {"tags": "Array<String>"}}
        engine = RuleEngine(schema)
        ctx = {"customer": {"tags": ["a"]}}
        rule = 'RULE r LANGUAGE 2 WHEN LENGTH(customer.tags) == 1 THEN ALLOW END'

        r1 = engine.evaluate(rule, copy.deepcopy(ctx))
        r2 = engine.evaluate(rule, copy.deepcopy(ctx))

        assert r1.decisions[0].matched == r2.decisions[0].matched
        assert engine._cache_hits == 1
        assert engine._cache_misses == 1
