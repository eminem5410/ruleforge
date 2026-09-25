using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using RuleForge.Core.Lexing;
using RuleForge.Core.Parsing;
using RuleForge.Core.Semantic;
using RuleForge.Core.Evaluation;

namespace RuleForge.Benchmarks;

public class Program
{
    static readonly Dictionary<string, Dictionary<string, string>> Schema = new()
    {
        { "customer", new Dictionary<string, string> { { "age", "Integer" }, { "name", "String" }, { "active", "Boolean" }, { "email", "String" } } }
    };

    static readonly Dictionary<string, object?> Context = new()
    {
        { "customer", new Dictionary<string, object?> { { "age", 25 }, { "name", "Pablo Diez" }, { "active", true }, { "email", "pablo@test.com" } } }
    };

    static readonly string RuleSimple = "RULE r LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END";
    static readonly string RuleComplex = "RULE r LANGUAGE 1 WHEN customer.age >= 18 AND customer.active == true OR contains(customer.name, \"Pablo\") AND customer.email IS NOT NULL THEN ALLOW END";

    public static void Main(string[] args)
    {
        Console.WriteLine("=========================================");
        Console.WriteLine(" RuleForge .NET 8 Benchmark ");
        Console.WriteLine($" CPU Cores: {Environment.ProcessorCount}");
        Console.WriteLine($" OS: {Environment.OSVersion}");
        Console.WriteLine("=========================================\n");

        Console.WriteLine("Warming up...");
        RunEvaluation(RuleSimple);

        Console.WriteLine("Running benchmarks...\n");
        RunBenchmark("Simple Rule (1 condition)", RuleSimple, 1000);
        RunBenchmark("Complex Rule (5 conditions)", RuleComplex, 1000);

        var multiRules = string.Join("\n", Enumerable.Range(0, 100).Select(i => RuleSimple.Replace("RULE r", $"RULE r{i}")));
        RunBenchmark("100 Rules in 1 Source File", multiRules, 100);
    }

    static void RunBenchmark(string name, string ruleSource, int iterations)
    {
        var times = new List<double>();
        var watch = new Stopwatch();

        for (int i = 0; i < iterations; i++)
        {
            watch.Start();
            RunEvaluation(ruleSource);
            watch.Stop();
            times.Add(watch.Elapsed.TotalMilliseconds);
            watch.Reset();
        }

        times.Sort();
        double mean = times.Average();
        double p95 = times[(int)(times.Count * 0.95)];
        double p99 = times[(int)(times.Count * 0.99)];
        int evalPerSec = (int)(1000 / mean);

        Console.WriteLine($"--- {name} ---");
        Console.WriteLine($"  Evaluations: {iterations}");
        Console.WriteLine($"  Mean Latency: {mean:F4} ms");
        Console.WriteLine($"  P95 Latency:  {p95:F4} ms");
        Console.WriteLine($"  P99 Latency:  {p99:F4} ms");
        Console.WriteLine($"  Throughput:   {evalPerSec:N0} eval/sec");
        Console.WriteLine();
    }

    static void RunEvaluation(string ruleSource)
    {
        var tokens = new Lexer(ruleSource).Tokenize();
        var ast = new Parser(tokens).Parse();
        new SemanticAnalyzer(Schema).Analyze(ast);
        new Evaluator(Context).EvaluateRules(ast);
    }
}
