import sys
import json
import os
from ruleforge import RuleForgeEngine, LexerError, ParserError, SemanticError, EvaluatorError

def run_eval(rule_path, data_path, schema_path, explain=False):
    for p in [rule_path, data_path, schema_path]:
        if not os.path.exists(p): return print(f"❌ Error: Archivo no encontrado: {p}")

    with open(rule_path, 'r', encoding='utf-8') as f: source_code = f.read()
    with open(data_path, 'r', encoding='utf-8') as f: context = json.load(f)
    with open(schema_path, 'r', encoding='utf-8') as f: schema = json.load(f)

    try:
        engine = RuleForgeEngine(schema)
        decisions = engine.evaluate(source_code, context, explain=explain)
        
        print(f"\n📊 Evaluando {len(decisions)} regla(s) contra el contexto...")
        for d in decisions:
            if explain:
                print(f"\n--- TRACE '{d.rule_id}' ---")
                for step in d.trace: print(f"  ➜ {step}")
                    
            print(f"\n--- DECISIÓN ---")
            print(f"Regla      : {d.rule_id}")
            print(f"Match      : {d.matched}")
            for act in d.actions:
                print(f"Acción     : {act.action_type}", end="")
                if act.value and act.value != 'None': print(f" (Mensaje: {act.value})")
                else: print("")
            print("----------------")
    except (LexerError, ParserError, SemanticError, EvaluatorError) as e:
        print(f"\n🛑 {e}\n")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}\n")

if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[1] == 'eval': run_eval(sys.argv[2], sys.argv[3], sys.argv[4], explain=False)
    elif len(sys.argv) == 5 and sys.argv[1] == 'explain': run_eval(sys.argv[2], sys.argv[3], sys.argv[4], explain=True)
    else:
        print("Uso:")
        print("  python3 cli.py eval <regla.rf> <datos.json> <schema.json>")
        print("  python3 cli.py explain <regla.rf> <datos.json> <schema.json>")
