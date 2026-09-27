import os, json, glob, sys
from ruleforge.lexer import Lexer, LexerError
from ruleforge.parser import Parser, ParserError
from ruleforge.semantic import SemanticAnalyzer, SemanticError
from ruleforge.evaluator import Evaluator, EvaluatorError
from ruleforge.engine import RuleEngine

SCHEMA = {
    "customer": {"age": "Integer", "name": "String", "active": "Boolean", "email": "String", "tags": "Array<String>", "birth_date": "Date", "registration_date": "Date", "id": "Integer", "risk_score": "Integer", "status": "String"},
    "invoice": {"total": "Decimal", "amount": "Decimal", "status": "String", "issue_date": "Date", "due_date": "Date"},
    "observation": {"code": "String", "value": "Decimal", "unit": "String"}
}

def get_result(rule_path, data_path, use_compiler):
    with open(rule_path) as f: source = f.read()
    with open(data_path) as f: data = json.load(f)
    try:
        ctx = data.get("context", {})
        engine = RuleEngine(SCHEMA, use_compiler=use_compiler)
        decisions = engine.evaluate(source, ctx).decisions
        d = decisions[-1]
        
        actions = [{"action_type": a.action_type, "value": a.value, "payload": a.payload} for a in d.actions]
        return {"code": None, "matched": d.matched, "actions": actions}
    except (LexerError, ParserError, SemanticError, EvaluatorError) as e:
        return {"code": e.code, "matched": False, "actions": []}

def main():
    rule_files = sorted(glob.glob("tests/conformance/**/*.rf", recursive=True))
    all_match = True
    
    for rule_path in rule_files:
        data_path = rule_path.replace('.rf', '.json')
        interp_res = get_result(rule_path, data_path, False)
        comp_res = get_result(rule_path, data_path, True)
        
        vector_name = os.path.basename(rule_path).replace('.rf', '')
        if interp_res == comp_res:
            print(f"{vector_name}: MATCH ✅")
        else:
            print(f"{vector_name}: MISMATCH ❌")
            print(f"  Interp: {interp_res}")
            print(f"  Comp  : {comp_res}")
            all_match = False
            
    if all_match:
        print("\n=== COMPILER CONFORMANCE: 100% MATCH ===")
        sys.exit(0)
    else:
        print("\n=== COMPILER CONFORMANCE: FAILURES DETECTED ===")
        sys.exit(1)

if __name__ == "__main__":
    main()
