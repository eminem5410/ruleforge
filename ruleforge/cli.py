import argparse
import json
import os
import sys

# Asegurar que el paquete ruleforge sea importable sin instalarlo globalmente
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ruleforge.engine import RuleEngine
from ruleforge.parser import ParserError
from ruleforge.semantic import SemanticError
from ruleforge.lexer import LexerError
from ruleforge.formatter import infer_schema, format_decision, format_trace, format_error

def main():
    parser = argparse.ArgumentParser(prog="ruleforge", description="RuleForge CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Comando: eval
    eval_parser = subparsers.add_parser("eval", help="Evaluate a rule file against a context")
    eval_parser.add_argument("rule_file", help="Path to the .rf rule file")
    eval_parser.add_argument("--context", help="JSON string representing the context", required=True)
    eval_parser.add_argument("--schema", help="JSON string representing the schema (optional)", required=False)
    eval_parser.add_argument("--trace", action="store_true", help="Enable deep trace output")

    # Comando: check
    check_parser = subparsers.add_parser("check", help="Validate rule syntax and semantics without evaluating")
    check_parser.add_argument("rule_file", help="Path to the .rf rule file")
    check_parser.add_argument("--schema", help="JSON string representing the schema (optional)", required=False)

    # Comando: trace
    trace_parser = subparsers.add_parser("trace", help="Evaluate rules and output a diagnostic trace")
    trace_parser.add_argument("rule_file", help="Path to the .rf rule file")
    trace_parser.add_argument("--context", help="JSON string representing the context", required=True)
    trace_parser.add_argument("--schema", help="JSON string representing the schema (optional)", required=False)

    args = parser.parse_args()

    if args.command == "eval":
        try:
            with open(args.rule_file, 'r') as f:
                code = f.read()
        except FileNotFoundError:
            print(f"❌ File not found: {args.rule_file}")
            sys.exit(1)

        try:
            context = json.loads(args.context)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid context JSON: {e}")
            sys.exit(1)

        schema = None
        if args.schema:
            try:
                schema = json.loads(args.schema)
            except json.JSONDecodeError as e:
                print(f"❌ Invalid schema JSON: {e}")
                sys.exit(1)
        else:
            schema = infer_schema(context)

        engine = RuleEngine(schema, use_compiler=False, max_cache_size=100)

        try:
            result = engine.evaluate(code, context, trace=args.trace)
            if result.decisions:
                for i, d in enumerate(result.decisions):
                    print(format_decision(d))
                    if args.trace and result.trace:
                        if i < len(result.trace):
                            print(format_trace(result.trace[i]))
            else:
                print("⚪ No decisions returned.")
        except Exception as e:
            print(format_error(e))
            sys.exit(1)

    elif args.command == "check":
        try:
            with open(args.rule_file, 'r') as f:
                code = f.read()
        except FileNotFoundError:
            print(f"❌ File not found: {args.rule_file}")
            sys.exit(1)

        schema = {}
        if args.schema:
            try:
                schema = json.loads(args.schema)
            except json.JSONDecodeError as e:
                print(f"❌ Invalid schema JSON: {e}")
                sys.exit(1)

        engine = RuleEngine(schema, use_compiler=False, max_cache_size=100)

        try:
            ast_list = engine.check(code)
            print("✓ Valid")
            print(f"  Rules: {len(ast_list)}")
            if ast_list:
                print(f"  Language: {ast_list[0].lang_version}")
        except (LexerError, ParserError, SemanticError) as e:
            print(format_error(e))
            sys.exit(1)
        except Exception as e:
            print(format_error(e))
            sys.exit(1)

    elif args.command == "trace":
        try:
            with open(args.rule_file, 'r') as f:
                code = f.read()
        except FileNotFoundError:
            print(f"❌ File not found: {args.rule_file}")
            sys.exit(1)

        try:
            context = json.loads(args.context)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid context JSON: {e}")
            sys.exit(1)

        schema = None
        if args.schema:
            try:
                schema = json.loads(args.schema)
            except json.JSONDecodeError as e:
                print(f"❌ Invalid schema JSON: {e}")
                sys.exit(1)
        else:
            schema = infer_schema(context)

        engine = RuleEngine(schema, use_compiler=False, max_cache_size=100)

        try:
            result = engine.evaluate(code, context, trace=True)
            if result.trace:
                for entry in result.trace:
                    print(format_trace(entry))
            else:
                print("⚪ No trace returned.")
        except Exception as e:
            print(format_error(e))
            sys.exit(1)

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
