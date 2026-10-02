import cmd
import json
import os
import sys

# Asegurar que el paquete ruleforge sea importable sin instalarlo globalmente
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ruleforge.engine import RuleEngine

class RuleForgeREPL(cmd.Cmd):
    intro = "RuleForge REPL v11.9.0. Type '.help' for commands. Type '.exit' to quit."
    prompt = "rf> "

    def __init__(self):
        super().__init__()
        self.context = {}
        self.schema = None  # None significa que no hay schema explícito
        self.trace = False
        self.engine = RuleEngine({"fields": {}}, use_compiler=False, max_cache_size=100)
        self._in_rule = False
        self._rule_buffer = []

    def _infer_schema(self, obj):
        schema = {}
        for k, v in obj.items():
            if isinstance(v, bool): schema[k] = "Boolean"
            elif isinstance(v, int): schema[k] = "Integer"
            elif isinstance(v, float): schema[k] = "Decimal"
            elif isinstance(v, str): schema[k] = "String"
            elif isinstance(v, dict): schema[k] = self._infer_schema(v)
            elif isinstance(v, list) and v: schema[k] = f"Array<{self._infer_schema(v[0])}>"
        return schema

    def emptyline(self):
        if self._in_rule:
            self._rule_buffer.append("")
        return

    def precmd(self, line):
        if line.startswith("."):
            stripped = line[1:].strip()
            if not stripped:
                return "empty"
            parts = stripped.split(" ", 1)
            cmd_name = parts[0]
            cmd_args = parts[1] if len(parts) > 1 else ""
            return f"{cmd_name} {cmd_args}"

        if self._in_rule:
            self._rule_buffer.append(line)
            if line.strip().upper() == "END":
                self._in_rule = False
                self.prompt = "rf> "
                code = "\n".join(self._rule_buffer)
                self._rule_buffer = []
                return f"eval_rule {code}"
            return ""
        
        if line.strip().upper().startswith("RULE ") and line.strip().upper().endswith("END"):
            return f"eval_rule {line}"
            
        if line.strip().upper().startswith("RULE "):
            self._in_rule = True
            self._rule_buffer = [line]
            self.prompt = "...> "
            return ""

        return line

    def do_eval_rule(self, arg):
        if not self.context:
            print("⚠️  Context is empty. Set it first using .context {...}")
            return
        
        try:
            result = self.engine.evaluate(arg, self.context, trace=self.trace)
            if result.decisions:
                for d in result.decisions:
                    print(f"✅ MATCH: {d.matched} | Actions: {[a.to_dict() for a in d.actions]}")
                    if self.trace and d.trace:
                        print("   Trace:")
                        print(json.dumps(d.trace, indent=2))
            else:
                print("⚪ No decisions returned.")
        except Exception as e:
            print(f"❌ Evaluation Error: {e}")

    def do_empty(self, arg):
        pass

    def do_exit(self, arg):
        """Exit the REPL."""
        print("Exiting RuleForge REPL.")
        return True

    def do_context(self, arg):
        """Set the evaluation context. Usage: .context {"customer": {"age": 25}}"""
        try:
            self.context = json.loads(arg)
            if self.schema is None:
                # Auto-infer schema if no explicit schema was set
                inferred = self._infer_schema(self.context)
                self.engine = RuleEngine(inferred, use_compiler=False, max_cache_size=100)
                print("✅ Context updated. Schema: auto-inferred")
            else:
                print("✅ Context updated. Schema: explicit")
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON: {e}")

    def do_schema(self, arg):
        """Set the engine schema. Usage: .schema {"customer": {"age": "Integer"}}"""
        try:
            self.schema = json.loads(arg)
            self.engine = RuleEngine(self.schema, use_compiler=False, max_cache_size=100)
            print("✅ Schema updated and engine reinitialized (explicit).")
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON: {e}")
        except Exception as e:
            print(f"❌ Engine error: {e}")

    def do_trace(self, arg):
        """Toggle deep trace. Usage: .trace on|off"""
        if arg.strip().lower() == "on":
            self.trace = True
            print("✅ Deep trace enabled.")
        elif arg.strip().lower() == "off":
            self.trace = False
            print("✅ Deep trace disabled.")
        else:
            print("Usage: .trace on|off")

if __name__ == "__main__":
    RuleForgeREPL().cmdloop()
