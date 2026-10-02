import time
import statistics
from ruleforge.engine import RuleEngine
from ruleforge.evaluator.evaluator import Evaluator

# --- Monkey-patch para instrumentar el Evaluator ---
original_eval = Evaluator._eval_node_impl
node_stats = {}

def profiled_eval(self, node):
    node_type = type(node).__name__
    if hasattr(node, 'type'):
        node_type = node.type
    
    start = time.perf_counter()
    result = original_eval(self, node)
    end = time.perf_counter()
    
    if node_type not in node_stats:
        node_stats[node_type] = {"calls": 0, "own_time": 0.0}
    
    node_stats[node_type]["calls"] += 1
    node_stats[node_type]["own_time"] += (end - start)
    
    return result

Evaluator._eval_node_impl = profiled_eval

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
END'''
}

print("=== RuleForge Evaluator Node Profile V11.8.2 ===\n")

global_stats = {}

for name, code in rules.items():
    node_stats.clear()
    engine = RuleEngine(schema, max_cache_size=100)
    
    # Warmup
    for _ in range(100):
        engine.evaluate(code, context)
    
    # Medición real (1000 iteraciones)
    for _ in range(1000):
        engine.evaluate(code, context)
        
    print(f"--- {name} ---")
    sorted_stats = sorted(node_stats.items(), key=lambda x: x[1]["calls"], reverse=True)
    for n_type, stats in sorted_stats[:5]: 
        calls = stats["calls"]
        total_time_ms = stats["own_time"] * 1000
        per_call_us = (total_time_ms / calls) * 1000 if calls > 0 else 0
        print(f"   {n_type:<25}: {calls:>6} calls | {total_time_ms:>7.2f} ms total | {per_call_us:>5.2f} µs/call")
        
        if n_type not in global_stats:
            global_stats[n_type] = {"calls": 0, "own_time": 0.0}
        global_stats[n_type]["calls"] += calls
        global_stats[n_type]["own_time"] += stats["own_time"]
    print()

print("=== Aggregate (All Rules) ===")
sorted_global = sorted(global_stats.items(), key=lambda x: x[1]["calls"], reverse=True)
for n_type, stats in sorted_global:
    calls = stats["calls"]
    total_time_ms = stats["own_time"] * 1000
    per_call_us = (total_time_ms / calls) * 1000 if calls > 0 else 0
    print(f"   {n_type:<25}: {calls:>6} calls | {total_time_ms:>7.2f} ms total | {per_call_us:>5.2f} µs/call")

Evaluator._eval_node_impl = original_eval
