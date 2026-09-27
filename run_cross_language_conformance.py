import os, json, glob, subprocess, sys
from ruleforge.lexer import Lexer, LexerError
from ruleforge.parser import Parser, ParserError
from ruleforge.semantic import SemanticAnalyzer, SemanticError
from ruleforge.evaluator import Evaluator, EvaluatorError

SCHEMA = {
    "customer": {"age": "Integer", "name": "String", "active": "Boolean", "email": "String", "tags": "Array<String>"},
    "invoice": {"total": "Decimal", "amount": "Integer", "status": "String"},
    "observation": {"code": "String", "value": "Decimal", "unit": "String"}
}

def get_python_result(rule_path, data_path):
    with open(rule_path) as f: source = f.read()
    with open(data_path) as f: data = json.load(f)
    try:
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()
        SemanticAnalyzer(SCHEMA).analyze(ast)
        ctx = data.get("context", {})
        eval = Evaluator(ctx)
        decisions = eval.eval_rules(ast)
        d = decisions[0]
        actions = [{"action_type": a.action_type, "value": a.value} for a in d.actions]
        return {"code": None, "matched": d.matched, "actions": actions}
    except (LexerError, ParserError, SemanticError, EvaluatorError) as e:
        return {"code": e.code, "matched": False, "actions": []}

def get_csharp_result(rule_path, data_path):
    # Usamos la DLL compilada directamente para mayor velocidad
    dll_path = "dotnet/src/RuleForge.ConformanceRunner/bin/Debug/net8.0/RuleForge.ConformanceRunner.dll"
    result = subprocess.run(["dotnet", dll_path, rule_path, data_path], capture_output=True, text=True)
    if result.returncode != 0:
        return {"code": "CSHARP_CRASH", "matched": False, "actions": []}
    return json.loads(result.stdout)

def main():
    rule_files = sorted(glob.glob("tests/conformance/**/*.rf", recursive=True))
    all_match = True
    
    for rule_path in rule_files:
        data_path = rule_path.replace('.rf', '.json')
        py_res = get_python_result(rule_path, data_path)
        cs_res = get_csharp_result(rule_path, data_path)
        
        vector_name = os.path.basename(rule_path).replace('.rf', '')
        if py_res == cs_res:
            print(f"{vector_name}: MATCH ✅")
        else:
            print(f"{vector_name}: MISMATCH ❌")
            print(f"  Python: {py_res}")
            print(f"  C#    : {cs_res}")
            all_match = False
            
    if all_match:
        print("\n=== CROSS-LANGUAGE CONFORMANCE: 100% MATCH ===")
        sys.exit(0)
    else:
        print("\n=== CROSS-LANGUAGE CONFORMANCE: FAILURES DETECTED ===")
        sys.exit(1)

if __name__ == "__main__":
    main()
