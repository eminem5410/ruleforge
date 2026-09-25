import json
import os
import sys
import glob
from decimal import Decimal
from datetime import date

# Agregar el paquete al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ruleforge import RuleForgeEngine
from ruleforge.lexer import LexerError
from ruleforge.parser import ParserError
from ruleforge.semantic import SemanticError
from ruleforge.evaluator import EvaluatorError

class RuleForgeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal): return str(obj)
        if isinstance(obj, date): return obj.isoformat()
        return super().default(obj)

def run_vectors():
    vector_dir = os.path.dirname(__file__)
    vector_files = glob.glob(os.path.join(vector_dir, "*.json"))
    
    passed = 0
    failed = 0
    
    for file_path in sorted(vector_files):
        with open(file_path, 'r') as f:
            vector = json.load(f)
            
        print(f"Running {vector['id']}: {vector['name']}... ", end="")
        
        try:
            engine = RuleForgeEngine(vector['context_schema'])
            decisions = engine.evaluate(vector['source'], vector['context'])
            
            actual_output = {
                "status": "ok",
                "decisions": [{"rule_id": d.rule_id, "matched": d.matched, "actions": [{"type": a.action_type, "value": a.value} for a in d.actions]} for d in decisions]
            }
            
            if actual_output == vector['expected']:
                print("PASS")
                passed += 1
            else:
                print("FAIL (Mismatch)")
                print(f"  Expected: {vector['expected']}")
                print(f"  Actual:   {actual_output}")
                failed += 1
                
        except (LexerError, ParserError, SemanticError, EvaluatorError) as e:
            if vector['expected']['status'] == 'error' and e.code == vector['expected']['error_code']:
                print("PASS")
                passed += 1
            else:
                print("FAIL (Unexpected Error)")
                print(f"  Expected: {vector['expected']}")
                print(f"  Actual Error: {e.code} - {e.message}")
                failed += 1
        except Exception as e:
            print("FAIL (Crash)")
            print(f"  Exception: {e}")
            failed += 1
            
    print(f"\nConformance Summary: {passed} passed, {failed} failed out of {passed+failed}.")
    return failed == 0

if __name__ == "__main__":
    success = run_vectors()
    sys.exit(0 if success else 1)
