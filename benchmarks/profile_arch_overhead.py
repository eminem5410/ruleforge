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

code_filter = '''RULE R LANGUAGE 1
WHEN LENGTH(
    FILTER customer.tags
    WHERE it == "a"
) == 2
THEN ALLOW
END
'''

engine = RuleEngine(schema, max_cache_size=100, use_compiler=False)

# Warmup
for _ in range(100):
    engine.evaluate(code_filter, context)

print("=== Architectural Overhead Profile (FILTER Rule - 10k iterations) ===")
profiler = cProfile.Profile()
profiler.enable()

for _ in range(10000):
    engine.evaluate(code_filter, context)

profiler.disable()

s = io.StringIO()
stats = pstats.Stats(profiler, stream=s)
stats.sort_stats('tottime') # Ordenar por tiempo EXCLUSIVO (tottime)
stats.print_stats(30) # Top 30 funciones
print(s.getvalue())
