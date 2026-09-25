import json
import os
import sys
import glob
from decimal import Decimal
from datetime import date
import argparse

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

def run_vectors(verbose=False):
    base_dir = os.path.dirname(__file__)
    manifest_path = os.path.join(base_dir, "manifest.json")
    
    if not os.path.exists(manifest_path):
        print("manifest.json not found!")
        return False
        
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
        
    passed = 0
    failed = 0
    total = len(manifest['vectors'])
    
    print("RuleForge Cross-Language Conformance")
    print("====================================")
    print(f"Contract Version: {manifest['contract_version']}")
    print(f"Language Version: {manifest['language_version']}")
    print(f"Vectors found: {total}\n")
    
    for vec_file in manifest['vectors']:
        file_path = os.path.join(base_dir, vec_file)
        with open(file_path, 'r') as f:
            vector = json.load(f)
            
        try:
            engine = RuleForgeEngine(vector['context_schema'])
            decisions = engine.evaluate(vector['source'], vector['context'])
            
            actual_output = {
                "status": "ok",
                "decisions": [{"rule_id": d.rule_id, "matched": d.matched, "actions": [{"type": a.action_type, "value": a.value} for a in d.actions]} for d in decisions]
            }
            
            if actual_output == vector['expected']:
                status_str = "PASS"
                passed += 1
            else:
                status_str = "FAIL (Mismatch)"
                failed += 1
                
            if verbose and status_str == "PASS":
                print(f"[{vector['id']}] {status_str} - {vector['name']}")
                print(f"  Output: {json.dumps(actual_output, cls=RuleForgeEncoder)}")
            elif status_str != "PASS":
                print(f"[{vector['id']}] {status_str} - {vector['name']}")
                print(f"  Expected: {json.dumps(vector['expected'])}")
                print(f"  Actual:   {json.dumps(actual_output, cls=RuleForgeEncoder)}")
            else:
                print(f"[{vector['id']}] {status_str} - {vector['name']}")
                
        except (LexerError, ParserError, SemanticError, EvaluatorError) as e:
            if vector['expected']['status'] == 'error' and e.code == vector['expected']['error_code']:
                status_str = "PASS"
                passed += 1
                if verbose:
                    print(f"[{vector['id']}] {status_str} - {vector['name']}")
                    print(f"  Error: {e.code} - {e.message}")
                else:
                    print(f"[{vector['id']}] {status_str} - {vector['name']}")
            else:
                status_str = "FAIL (Unexpected Error)"
                failed += 1
                print(f"[{vector['id']}] {status_str} - {vector['name']}")
                print(f"  Expected: {json.dumps(vector['expected'])}")
                print(f"  Actual Error: {e.code} - {e.message}")
        except Exception as e:
            status_str = "FAIL (Crash)"
            failed += 1
            print(f"[{vector['id']}] {status_str} - {vector['name']}")
            print(f"  Exception: {e}")
            
    print("------------------------------------")
    print(f"{passed} passed, {failed} failed out of {total}.")
    if failed == 0:
        print("\nCONFORMANCE PASS")
    else:
        print("\nCONFORMANCE FAIL")
        
    return failed == 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RuleForge Cross-Language Conformance Runner")
    parser.add_argument("--verbose", action="store_true", help="Show full output for passing tests")
    args = parser.parse_args()
    
    success = run_vectors(verbose=args.verbose)
    sys.exit(0 if success else 1)
