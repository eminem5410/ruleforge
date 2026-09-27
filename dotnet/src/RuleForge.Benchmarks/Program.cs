using System.Diagnostics;
using System.Collections.Generic;
using RuleForge.Core.Lexing;
using RuleForge.Core.Parsing;
using RuleForge.Core.Semantic;
using RuleForge.Core.Evaluation;
using RuleForge.Core.Compilation;

var rule = "RULE r LANGUAGE 2 WHEN LENGTH(customer.name) >= 4 AND CONTAINS(customer.email, \"@\") THEN ALLOW END";
var schema = new Dictionary<string, Dictionary<string, string>> { { "customer", new() { {"name", "String"}, {"email", "String"} } } };
var ctx = new Dictionary<string, object?> { { "customer", new Dictionary<string, object?> { {"name", "admin"}, {"email", "admin@test.com"} } } };

var tokens = new Lexer(rule).Tokenize();
var ast = new Parser(tokens).Parse();
new SemanticAnalyzer(schema).Analyze(ast);

var evaluator = new Evaluator(ctx);
var compiler = new RuleForgeCompiler(ast);

int[] scales = { 10_000, 100_000, 1_000_000 };

Console.WriteLine("Warming up...");
for(int i=0; i<1000; i++) { evaluator.EvaluateRules(ast); compiler.Execute(ctx); }

foreach (var iterations in scales) {
    Console.WriteLine($"\n=== {iterations:N0} Iterations ===");
    
    var sw = Stopwatch.StartNew();
    for(int i=0; i<iterations; i++) evaluator.EvaluateRules(ast);
    sw.Stop();
    double interpMs = sw.Elapsed.TotalMilliseconds;
    Console.WriteLine($"Interpreter: {interpMs:F2}ms ({iterations / sw.Elapsed.TotalSeconds:F0} ops/sec)");

    sw.Restart();
    for(int i=0; i<iterations; i++) compiler.Execute(ctx);
    sw.Stop();
    double compMs = sw.Elapsed.TotalMilliseconds;
    Console.WriteLine($"Compiled:    {compMs:F2}ms ({iterations / sw.Elapsed.TotalSeconds:F0} ops/sec)");
    Console.WriteLine($"Speedup:     {interpMs / compMs:F2}x");
}
