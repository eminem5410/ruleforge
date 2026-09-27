import time
from ruleforge.lexer import Lexer
from ruleforge.parser import Parser
from ruleforge.semantic import SemanticAnalyzer
from ruleforge.evaluator import Evaluator
from ruleforge.compiler import RuleForgeCompiler

SCHEMA = {"customer": {"age": "Integer", "active": "Boolean"}}
RULE = "RULE r LANGUAGE 2 WHEN customer.age >= 18 AND customer.active == true THEN ALLOW END"
CONTEXT = {"customer": {"age": 21, "active": True}}

tokens = Lexer(RULE).tokenize()
ast = Parser(tokens).parse()
SemanticAnalyzer(SCHEMA).analyze(ast)

evaluator = Evaluator(CONTEXT)
compiler = RuleForgeCompiler(ast)

ITERATIONS = 100000

print(f"Running benchmark with {ITERATIONS:,} iterations...")

# Benchmark Interpreter
start = time.perf_counter()
for _ in range(ITERATIONS):
    evaluator.eval_rules(ast)
interp_time = time.perf_counter() - start

# Benchmark Compiler
start = time.perf_counter()
for _ in range(ITERATIONS):
    compiler.execute(CONTEXT)
comp_time = time.perf_counter() - start

print(f"\n=== BENCHMARK RESULTS ===")
print(f"Iterations:  {ITERATIONS:,}")
print(f"Interpreter: {interp_time:.4f}s ({ITERATIONS/interp_time:,.0f} ops/sec)")
print(f"Compiled:     {comp_time:.4f}s ({ITERATIONS/comp_time:,.0f} ops/sec)")
print(f"Speedup:      {interp_time/comp_time:.2f}x")
