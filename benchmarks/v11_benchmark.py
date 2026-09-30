"""V11.4 Block 4: Comprehensive benchmarks.

Separates:
A) Full pipeline (Lexer → Parser → Semantic → Engine)
B) Evaluation only (pre-built AST → Interpreter)
C) Evaluation only (pre-built AST → Compiler)
D) Multi-rule scaling (50/100/250/500 rules)
E) Array scaling (10/50/100/250/500 elements)
"""
import time
import statistics
import copy
from decimal import Decimal
from ruleforge import RuleEngine
from ruleforge.lexer import Lexer
from ruleforge.parser import Parser
from ruleforge.semantic import SemanticAnalyzer
from ruleforge.evaluator import Evaluator
from ruleforge.compiler import RuleForgeCompiler

SCHEMA = {
    "customer": {
        "age": "Integer", "active": "Boolean", "email": "String",
        "tags": "Array<String>", "risk_score": "Integer", "status": "String",
    },
    "invoice": {"total": "Decimal", "status": "String"},
}

CONTEXT = {
    "customer": {
        "age": 25, "active": True, "email": "pablo@test.com",
        "tags": ["a", "b", "c", "d", "e"],
        "risk_score": 50, "status": "active",
    },
    "invoice": {"total": Decimal("100.50"), "status": "PENDING"},
}

RULES = {
    "simple": 'RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END',
    "complex": 'RULE r LANGUAGE 1 WHEN customer.age >= 18 AND customer.active == true OR customer.email IS NOT NULL THEN ALLOW END',
    "any_5": 'RULE r LANGUAGE 2 WHEN ANY customer.tags WHERE it == "a" THEN ALLOW END',
    "filter_5": 'RULE r LANGUAGE 2 WHEN LENGTH(FILTER customer.tags WHERE it == "a") == 1 THEN ALLOW END',
}


def make_multi_rule(n):
    return "\n".join([f'RULE r{i} LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END' for i in range(n)])


def make_array_any(n):
    elements = ", ".join("0" for _ in range(n))
    return f'RULE r LANGUAGE 2 WHEN ANY [{elements}] WHERE it > 0 THEN ALLOW END'


def make_array_filter(n):
    elements = ", ".join(str(i) for i in range(1, n + 1))
    return f'RULE r LANGUAGE 2 WHEN LENGTH(FILTER [{elements}] WHERE it > {n // 2}) == {n // 2} THEN ALLOW END'


def measure(func, iterations=1000):
    """Run func() iterations times, return stats in ms."""
    # Warmup
    func()
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        end = time.perf_counter()
        times.append((end - start) * 1000)
    mean_ms = statistics.mean(times)
    p50 = sorted(times)[len(times) // 2]
    p95 = sorted(times)[int(len(times) * 0.95)]
    ops = int(1000 / mean_ms) if mean_ms > 0 else 0
    return mean_ms, p50, p95, ops


def bench_pipeline(name, rule, context, use_compiler=False, trace=False, iterations=1000):
    """A) Full pipeline: Lexer -> Parser -> Semantic -> Engine."""
    engine = RuleEngine(SCHEMA, use_compiler=use_compiler)
    # Check if rule exceeds AST limits before benchmarking
    try:
        engine.evaluate(rule, copy.deepcopy(context), trace=trace)
    except Exception as e:
        print(f"  {name:<40s} | {'N/A':>8s} | {'N/A':>8s} | {'N/A':>8s} | {f'limit: {getattr(e, "code", "?")}':>10s}")
        return
    def run():
        ctx = copy.deepcopy(context)
        engine.evaluate(rule, ctx, trace=trace)
    mean, p50, p95, ops = measure(run, iterations)
    print(f"  {name:<40s} | {mean:>8.3f} ms | {p50:>8.3f} ms | {p95:>8.3f} ms | {ops:>8,} ops/s")


def bench_eval_only(name, rule_source, context, use_compiler=False, iterations=1000):
    """B/C) Evaluation only: pre-built AST, skip Lexer/Parser/Semantic."""
    tokens = Lexer(rule_source).tokenize()
    ast = Parser(tokens).parse()
    SemanticAnalyzer(SCHEMA).analyze(ast)

    if use_compiler:
        compiler = RuleForgeCompiler(ast)
        def run():
            ctx = copy.deepcopy(context)
            compiler.execute(ctx)
    else:
        def run():
            ctx = copy.deepcopy(context)
            ev = Evaluator(ctx)
            ev.eval_rules(ast)

    mean, p50, p95, ops = measure(run, iterations)
    print(f"  {name:<40s} | {mean:>8.3f} ms | {p50:>8.3f} ms | {p95:>8.3f} ms | {ops:>8,} ops/s")


def section(title):
    print(f"\n{'='*85}")
    print(f"  {title}")
    print(f"{'='*85}")
    print(f"  {'Rule':<40s} | {'Mean':>8s} | {'P50':>8s} | {'P95':>8s} | {'Throughput':>10s}")
    print(f"  {'-'*40}-+-{'-'*8}-+-{'-'*8}-+-{'-'*8}-+-{'-'*10}")


if __name__ == "__main__":
    print("=" * 85)
    print(f"  RuleForge V11.4 Benchmark")
    print(f"  Python {__import__('sys').version.split()[0]}")
    print("=" * 85)

    # --- A) Full pipeline (interpreter) ---
    section("A) Full Pipeline (Lexer→Parser→Semantic→Engine, Interpreter)")
    for name, rule in RULES.items():
        bench_pipeline(f"pipeline/interp/{name}", rule, CONTEXT, iterations=1000)

    # --- B) Evaluation only (interpreter) ---
    section("B) Evaluation Only (pre-built AST → Interpreter)")
    for name, rule in RULES.items():
        bench_eval_only(f"eval_only/interp/{name}", rule, CONTEXT, use_compiler=False, iterations=2000)

    # --- C) Evaluation only (compiler) ---
    section("C) Evaluation Only (pre-built AST → Compiler)")
    for name, rule in RULES.items():
        bench_eval_only(f"eval_only/comp/{name}", rule, CONTEXT, use_compiler=True, iterations=2000)

    # --- D) Multi-rule scaling ---
    section("D) Multi-Rule Scaling (Full Pipeline, Interpreter)")
    for n in [1, 10, 50, 100, 250]:
        iters = max(50, 1000 // n)
        bench_pipeline(f"interp/{n}_rules", make_multi_rule(n), CONTEXT, iterations=iters)

    section("D) Multi-Rule Scaling (Full Pipeline, Compiler)")
    for n in [1, 10, 50, 100, 250]:
        iters = max(50, 1000 // n)
        bench_pipeline(f"comp/{n}_rules", make_multi_rule(n), CONTEXT, use_compiler=True, iterations=iters)

    section("D) Multi-Rule Scaling (Eval Only, Interpreter)")
    for n in [1, 10, 50, 100, 250]:
        iters = max(50, 2000 // n)
        bench_eval_only(f"eval/interp/{n}_rules", make_multi_rule(n), CONTEXT, use_compiler=False, iterations=iters)

    section("D) Multi-Rule Scaling (Eval Only, Compiler)")
    for n in [1, 10, 50, 100, 250]:
        iters = max(50, 2000 // n)
        bench_eval_only(f"eval/comp/{n}_rules", make_multi_rule(n), CONTEXT, use_compiler=True, iterations=iters)

    # --- E) Array scaling ---
    section("E) Array Scaling (Full Pipeline, ANY)")
    for n in [10, 50, 100, 200, 400]:
        iters = max(50, 1000 // max(1, n // 10))
        bench_pipeline(f"any_{n}", make_array_any(n), {}, iterations=iters)

    section("E) Array Scaling (Full Pipeline, FILTER)")
    for n in [10, 50, 100, 200, 400]:
        iters = max(50, 1000 // max(1, n // 10))
        bench_pipeline(f"filter_{n}", make_array_filter(n), {}, iterations=iters)

    # --- Trace overhead (eval only) ---
    section("Trace Overhead (Eval Only, Interpreter)")
    for name, rule in [("simple", RULES["simple"]), ("complex", RULES["complex"])]:
        tokens = Lexer(rule).tokenize()
        ast = Parser(tokens).parse()
        SemanticAnalyzer(SCHEMA).analyze(ast)

        # trace=False
        def run_off():
            ctx = copy.deepcopy(CONTEXT)
            ev = Evaluator(ctx, deep_trace=False)
            ev.eval_rules(ast)
        mean, p50, p95, ops = measure(run_off, 2000)
        print(f"  eval/trace_off/{name:<22s} | {mean:>8.3f} ms | {p50:>8.3f} ms | {p95:>8.3f} ms | {ops:>8,} ops/s")

        # trace=True
        def run_on():
            ctx = copy.deepcopy(CONTEXT)
            ev = Evaluator(ctx, deep_trace=True)
            ev.eval_rules(ast)
        mean, p50, p95, ops = measure(run_on, 2000)
        print(f"  eval/trace_on/{name:<21s} | {mean:>8.3f} ms | {p50:>8.3f} ms | {p95:>8.3f} ms | {ops:>8,} ops/s")

    print(f"\n{'='*85}")
    print("  Benchmark complete.")
    print("=" * 85)
