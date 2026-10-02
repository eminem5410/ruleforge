import cProfile
import pstats
import io
from ruleforge.engine import RuleEngine

schema = {
    "customer": {
        "age": "Integer",
        "tags": "Array<String>"
    }
}
context = {
    "customer": {
        "age": 25,
        "tags": ["a", "b", "c", "a"]
    }
}

# Usamos la regla más compleja para que el Evaluator tenga trabajo real
code_complex = '''RULE R LANGUAGE 1
WHEN LENGTH(
    FILTER customer.tags
    WHERE it == "a"
) == 2
THEN ALLOW
END
'''

engine = RuleEngine(schema, max_cache_size=100)

# Warmup para que el cache guarde el AST
for _ in range(100):
    engine.evaluate(code_complex, context)

print("=== Runtime Breakdown (cProfile) - Warm Path FILTER Rule ===")
profiler = cProfile.Profile()
profiler.enable()

# 10,000 iteraciones para que los números sean significativos
for _ in range(10000):
    engine.evaluate(code_complex, context)

profiler.disable()

s = io.StringIO()
stats = pstats.Stats(profiler, stream=s)
stats.sort_stats('cumulative')
stats.print_stats(25) # Top 25 funciones que más tiempo consumen
print(s.getvalue())
