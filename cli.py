import sys
import json
import os
import argparse
from ruleforge import RuleForgeEngine
from ruleforge.lexer import LexerError
from ruleforge.parser import ParserError
from ruleforge.semantic import SemanticError
from ruleforge.evaluator import EvaluatorError

def main():
    parser = argparse.ArgumentParser(description="RuleForge Decision Engine CLI")
    subparsers = parser.add_subparsers(dest="command")

    for cmd in ["eval", "explain"]:
        p = subparsers.add_parser(cmd)
        p.add_argument("rule_path")
        p.add_argument("data_path")
        p.add_argument("schema_path")
        p.add_argument("--json", action="store_true", dest="json_output")

    args = parser.parse_args()

    if args.command not in ["eval", "explain"]:
        parser.print_help()
        sys.exit(2)

    for p in [args.rule_path, args.data_path, args.schema_path]:
        if not os.path.exists(p):
            print(f"❌ Error: Archivo no encontrado: {p}")
            sys.exit(2)

    try:
        with open(args.rule_path, 'r', encoding='utf-8') as f: source_code = f.read()
        with open(args.data_path, 'r', encoding='utf-8') as f: context = json.load(f)
        with open(args.schema_path, 'r', encoding='utf-8') as f: schema = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Error: JSON inválido: {e}")
        sys.exit(2)

    try:
        engine = RuleForgeEngine(schema)
        explain_mode = (args.command == "explain") or args.json_output
        decisions = engine.evaluate(source_code, context, explain=explain_mode)
        
        if args.json_output:
            output = {"decisions": [d.to_dict() for d in decisions]}
            print(json.dumps(output, indent=2))
        else:
            print(f"\n📊 Evaluando {len(decisions)} regla(s) contra el contexto...")
            for d in decisions:
                if args.command == "explain":
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
        sys.exit(0)
        
    except (LexerError, ParserError, SemanticError, EvaluatorError) as e:
        if args.json_output:
            print(json.dumps({"error": {"code": e.code, "message": str(e)}}, indent=2))
        else:
            print(f"\n🛑 {e}\n")
        sys.exit(1)
    except Exception as e:
        if args.json_output:
            print(json.dumps({"error": {"code": "INTERNAL", "message": str(e)}}, indent=2))
        else:
            print(f"\n❌ Error inesperado: {e}\n")
        sys.exit(2)

if __name__ == "__main__":
    main()
