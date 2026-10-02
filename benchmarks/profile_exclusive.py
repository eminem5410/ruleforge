import time
from ruleforge.engine import RuleEngine
from ruleforge.evaluator.evaluator import Evaluator

# --- Profiler con Exclusive Time ---
original_eval_node = Evaluator.eval_node
stats = {}

def profiled_eval_node(self, node):
    node_type = type(node).__name__
    if hasattr(node, 'type'):
        node_type = node.type
        
    start = time.perf_counter()
    
    # Inicializamos/limpiamos el acumulador de tiempo de hijos para este nodo
    if not hasattr(self, '_prof_child_stack'):
        self._prof_child_stack = []
        
    self._prof_child_stack.append(0.0)
    
    # Ejecutamos la función original
    result = original_eval_node(self, node)
    
    end = time.perf_counter()
    
    elapsed = end - start
    child_time = self._prof_child_stack.pop()
    exclusive_time = elapsed - child_time
    
    # Sumamos nuestro tiempo total al acumulador del padre (si existe)
    if self._prof_child_stack:
        self._prof_child_stack[-1] += elapsed
        
    if node_type not in stats:
        stats[node_type] = {"calls": 0, "inclusive": 0.0, "exclusive": 0.0}
        
    stats[node_type]["calls"] += 1
    stats[node_type]["inclusive"] += elapsed
    stats[node_type]["exclusive"] += exclusive_time
    
    return result

Evaluator.eval_node = profiled_eval_node

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

print("=== RuleForge Exclusive Evaluator Profile ===\n")

global_stats = {}

for name, code in rules.items():
    stats.clear()
    engine = RuleEngine(schema, max_cache_size=100)
    
    # Warmup
    for _ in range(100):
        engine.evaluate(code, context)
    
    # Medición
    for _ in range(1000):
        engine.evaluate(code, context)
        
    print(f"--- {name} ---")
    sorted_stats = sorted(stats.items(), key=lambda x: x[1]["exclusive"], reverse=True)
    for n_type, s in sorted_stats[:5]: 
        calls = s["calls"]
        inc_ms = s["inclusive"] * 1000
        exc_ms = s["exclusive"] * 1000
        exc_per_call_us = (exc_ms / calls) * 1000 if calls > 0 else 0
        print(f"   {n_type:<25}: {calls:>6} calls | Inc: {inc_ms:>7.2f} ms | Exc: {exc_ms:>7.2f} ms | {exc_per_call_us:>5.2f} µs/call")
        
        if n_type not in global_stats:
            global_stats[n_type] = {"calls": 0, "inclusive": 0.0, "exclusive": 0.0}
        global_stats[n_type]["calls"] += calls
        global_stats[n_type]["inclusive"] += s["inclusive"]
        global_stats[n_type]["exclusive"] += s["exclusive"]
    print()

print("=== AGGREGATE (All Rules) ===")
sorted_global = sorted(global_stats.items(), key=lambda x: x[1]["exclusive"], reverse=True)
for n_type, s in sorted_global:
    calls = s["calls"]
    inc_ms = s["inclusive"] * 1000
    exc_ms = s["exclusive"] * 1000
    exc_per_call_us = (exc_ms / calls) * 1000 if calls > 0 else 0
    print(f"   {n_type:<25}: {calls:>6} calls | Inc: {inc_ms:>7.2f} ms | Exc: {exc_ms:>7.2f} ms | {exc_per_call_us:>5.2f} µs/call")

Evaluator.eval_node = original_eval_node
