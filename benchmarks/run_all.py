import time
import statistics
from ruleforge.engine import RuleEngine

# --- Helper de Estadísticas ---
def run_benchmark(func, iterations=1000, warmup=100):
    # Warmup (asegura que el AST cache esté caliente)
    for _ in range(warmup):
        func()
    
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        end = time.perf_counter()
        times.append((end - start) * 1000) # ms
    
    times.sort()
    return {
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "p95": times[int(len(times) * 0.95)],
        "p99": times[int(len(times) * 0.99)],
    }

# --- Generadores de Contexto ---
def generate_context(size_kb):
    dummy_data = "x" * (size_kb * 1024)
    return {
        "customer": {
            "age": 25,
            "active": True,
            "email": "pablo@test.com",
            "tags": ["a", "b"],
            "data": dummy_data
        }
    }

# --- Baterías de Tests ---
def benchmark_cache():
    schema = {
        "customer": {
            "age": "Integer",
            "active": "Boolean",
            "email": "String",
            "tags": "Array<String>",
        }
    }
    code = '''
RULE TestRule LANGUAGE 1
WHEN customer.age >= 18
THEN ALLOW
END
'''
    context = generate_context(1)
    
    # Cold path (cache desactivado)
    cold_engine = RuleEngine(schema, use_compiler=False, max_cache_size=0)
    cold = run_benchmark(lambda: cold_engine.evaluate(code, context), iterations=100, warmup=0)
    
    # Warm path (cache activado)
    warm_engine = RuleEngine(schema, use_compiler=False, max_cache_size=100)
    warm = run_benchmark(lambda: warm_engine.evaluate(code, context), iterations=1000)
    
    return {"cold": cold, "warm": warm}

def benchmark_context_memory_scaling():
    # Esta prueba mide el impacto de deepcopy y validación de contexto,
    # no del Evaluator, ya que la regla solo lee customer.age.
    schema = {
        "customer": {
            "age": "Integer",
            "active": "Boolean",
            "email": "String",
            "tags": "Array<String>",
            "data": "String"
        }
    }
    code = '''
RULE TestRule LANGUAGE 1
WHEN customer.age >= 18
THEN ALLOW
END
'''
    engine = RuleEngine(schema)
    
    results = {}
    sizes = [1, 10, 100, 1000, 10000] # KB
    
    for size in sizes:
        ctx = generate_context(size)
        stats = run_benchmark(lambda: engine.evaluate(code, ctx), iterations=100, warmup=10)
        results[f"{size} KB"] = stats
        
    return results

def benchmark_rule_pipeline_scaling():
    schema = {
        "customer": {
            "age": "Integer",
            "active": "Boolean",
            "email": "String",
            "tags": "Array<String>",
        }
    }
    
    def generate_rules(count):
        rules = []
        for i in range(count):
            rules.append(f"""
RULE Rule_{i} LANGUAGE 1
WHEN customer.age >= {i}
THEN ALLOW
END
""")
        return "\n".join(rules)
    
    results = {}
    counts = [1, 10, 100, 1000]
    
    for count in counts:
        engine = RuleEngine(schema)
        context = generate_context(1)
        code = generate_rules(count)
        # Evaluamos TODAS las reglas en una sola llamada
        stats = run_benchmark(lambda: engine.evaluate(code, context), iterations=10, warmup=1)
        results[f"{count} rules"] = stats
        
    return results

if __name__ == "__main__":
    print("=== RuleForge Performance Baseline V11.8.0 ===\n")
    
    print("1. AST Cache (Cold vs Warm):")
    cache_stats = benchmark_cache()
    print(f"   Cold: {cache_stats['cold']['median']:.4f} ms (median) | P95: {cache_stats['cold']['p95']:.4f} ms")
    print(f"   Warm: {cache_stats['warm']['median']:.4f} ms (median) | P95: {cache_stats['warm']['p95']:.4f} ms\n")
    
    print("2. Context Memory Scaling (deepcopy/validator impact):")
    ctx_stats = benchmark_context_memory_scaling()
    for size, stats in ctx_stats.items():
        print(f"   {size:>7}: {stats['median']:.4f} ms (median) | P95: {stats['p95']:.4f} ms")
    
    print("\n3. Rule Pipeline Scaling (N Rules in 1 evaluation):")
    scaling_stats = benchmark_rule_pipeline_scaling()
    for count, stats in scaling_stats.items():
        print(f"   {count:>7}: {stats['median']:.4f} ms (median) | P95: {stats['p95']:.4f} ms")
        
    print("\n=== Baseline Complete ===")
