import time
import statistics
from ruleforge.engine import RuleEngine

def run_benchmark(func, iterations=1000, warmup=100):
    for _ in range(warmup):
        func()
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        end = time.perf_counter()
        times.append((end - start) * 1000)
    times.sort()
    return {
        "median": statistics.median(times),
        "p95": times[int(len(times) * 0.95)]
    }

schema = {
    "customer": {
        "age": "Integer",
        "active": "Boolean",
        "email": "String",
        "tags": "Array<String>"
    }
}

context = {
    "customer": {
        "age": 25,
        "active": True,
        "email": "pablo@test.com",
        "tags": ["a", "b", "c", "a"]
    }
}

rules = {
    "Simple": "RULE R LANGUAGE 1\nWHEN customer.age >= 18\nTHEN ALLOW\nEND",
    "Complex Bool": "RULE R LANGUAGE 1\nWHEN customer.age >= 18 AND customer.active == true OR customer.email IS NULL\nTHEN ALLOW\nEND",
    "Array": "RULE R LANGUAGE 1\nWHEN LENGTH(customer.tags) == 4\nTHEN ALLOW\nEND",
    "FILTER": '''RULE R LANGUAGE 1
WHEN LENGTH(
    FILTER customer.tags
    WHERE it == "a"
) == 2
THEN ALLOW
END''',
    "MAP": '''RULE R LANGUAGE 1
WHEN LENGTH(
    MAP customer.tags
    USING it
) == 4
THEN ALLOW
END''',
    "SET": "RULE R LANGUAGE 1\nWHEN customer.age >= 18\nTHEN SET customer.age = 30\nEND"
}

print("=== RuleForge Feature Benchmark V11.8.2 ===\n")
for name, code in rules.items():
    engine = RuleEngine(schema, max_cache_size=100)
    stats = run_benchmark(lambda: engine.evaluate(code, context))
    print(f"   {name:<15}: {stats['median']:.4f} ms (median) | P95: {stats['p95']:.4f} ms")
