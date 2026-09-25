import time
import statistics
from ruleforge import RuleForgeEngine

SCHEMA = {
    "customer": {"age": "Integer", "name": "String", "active": "Boolean", "email": "String"}
}
engine = RuleForgeEngine(SCHEMA)

RULE_SIMPLE = 'RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END'
RULE_COMPLEX = 'RULE r LANGUAGE 1 WHEN customer.age >= 18 AND customer.active == true OR contains(customer.name, "Pablo") AND customer.email IS NOT NULL THEN ALLOW END'

CONTEXT = {"customer": {"age": 25, "name": "Pablo Diez", "active": True, "email": "pablo@test.com"}}

def run_benchmark(name, rule, n, context=CONTEXT):
    times = []
    for _ in range(n):
        start = time.perf_counter()
        engine.evaluate(rule, context)
        end = time.perf_counter()
        times.append((end - start) * 1000)
    
    mean_ms = statistics.mean(times)
    p95_ms = sorted(times)[int(len(times) * 0.95)] if len(times) >= 20 else max(times)
    eval_per_sec = int(1000 / mean_ms) if mean_ms > 0 else float('inf')
    
    print(f"--- {name} ---")
    print(f"  Evaluations: {n}")
    print(f"  Mean Latency: {mean_ms:.4f} ms")
    print(f"  P95 Latency:  {p95_ms:.4f} ms")
    print(f"  Throughput:   {eval_per_sec:,} eval/sec")
    print("")

if __name__ == "__main__":
    print("=========================================")
    print(" RuleForge V1.3.1 Benchmark ")
    print(" Environment: Local Dev Machine ")
    print("=========================================\n")
    
    print("Warming up...")
    engine.evaluate(RULE_SIMPLE, CONTEXT)
    
    print("Running benchmarks...\n")
    run_benchmark("Simple Rule (1 condition)", RULE_SIMPLE, 1000)
    run_benchmark("Complex Rule (5 conditions)", RULE_COMPLEX, 1000)
    
    # Benchmark de 100 reglas en un solo archivo
    multi_rule_source = "\n".join([f'RULE r{i} LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END' for i in range(100)])
    run_benchmark("100 Rules in 1 Source File", multi_rule_source, 100)
