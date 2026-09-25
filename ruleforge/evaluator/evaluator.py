from decimal import Decimal, InvalidOperation
from datetime import date
from ..parser.ast_nodes import RuleNode, ActionNode, BinaryOpNode, UnaryOpNode, NullCheckNode, LiteralNode, IdentifierNode, PropertyAccessNode, FunctionCallNode
from .errors import EvaluatorError

MAX_EXECUTION_STEPS = 10000

def normalize_value(val):
    if isinstance(val, float): return Decimal(str(val))
    return val

class Decision:
    def __init__(self, rule_id, rule_version, language_version, matched, actions, trace=None):
        self.rule_id, self.rule_version, self.language_version = rule_id, rule_version, language_version
        self.matched, self.actions, self.trace = matched, actions, trace or []
    def to_dict(self):
        return {"rule_id": self.rule_id, "rule_version": self.rule_version, "language_version": self.language_version, "matched": self.matched, "actions": [a.to_dict() for a in self.actions], "trace": self.trace}

class Evaluator:
    def __init__(self, context, explain_mode=False):
        self.context, self.explain_mode, self.trace = context, explain_mode, []
        self.step_count = 0

    def eval_rules(self, ast_list):
        return [self.eval_rule(rule) for rule in ast_list]

    def eval_rule(self, node: RuleNode):
        self.trace, self.step_count = [], 0
        try:
            condition_result = self.eval_node(node.when_expr)
        except EvaluatorError: raise
        except Exception as e:
            raise EvaluatorError("RF4001", f"Unexpected runtime error: {e}")
            
        if self.explain_mode: self.trace.append(f"CONDICIÓN FINAL EVALUADA COMO: {condition_result}")
        actions = node.then_actions if condition_result else (node.else_actions if node.else_actions else [ActionNode("NO_ACTION")])
        return Decision(node.name, 1, node.lang_version, condition_result, actions, self.trace)

    def check_null(self, val, op):
        if val is None: raise EvaluatorError("RF4002", f"Runtime Type Error: Cannot perform '{op}' on NULL. Use IS NULL / IS NOT NULL.")

    def eval_node(self, node):
        self.step_count += 1
        if self.step_count > MAX_EXECUTION_STEPS:
            raise EvaluatorError("RF5003", f"Security Limit: Execution exceeded {MAX_EXECUTION_STEPS} steps")

        if isinstance(node, LiteralNode):
            if node.type == "BOOLEAN": return node.value == "true"
            if node.type == "INTEGER": return int(node.value)
            if node.type == "DECIMAL": return Decimal(node.value)
            if node.type == "DATE": y, m, d = map(int, node.value.split('-')); return date(y, m, d)
            return node.value
        elif isinstance(node, PropertyAccessNode):
            obj = self.context.get(node.obj)
            return normalize_value(obj.get(node.prop)) if obj else None
        elif isinstance(node, IdentifierNode): return normalize_value(self.context.get(node.name))
        elif isinstance(node, NullCheckNode):
            val = self.eval_node(node.left)
            result = val is not None if node.is_not else val is None
            if self.explain_mode: self.trace.append(f"Evaluando: {val} IS {'NOT ' if node.is_not else ''}NULL -> {result}")
            return result
        elif isinstance(node, UnaryOpNode):
            val = self.eval_node(node.operand)
            if node.op == "NOT":
                self.check_null(val, "NOT")
                result = not val
                if self.explain_mode: self.trace.append(f"Evaluando: NOT {val} -> {result}")
                return result
        elif isinstance(node, BinaryOpNode):
            op = node.op
            if op == "AND":
                l = self.eval_node(node.left)
                if not l:
                    if self.explain_mode: self.trace.append(f"Short-circuit AND: {l} AND ... -> False")
                    return False
                r = self.eval_node(node.right)
                if self.explain_mode: self.trace.append(f"Evaluando: {l} AND {r} -> {bool(r)}")
                return bool(r)
            elif op == "OR":
                l = self.eval_node(node.left)
                if l:
                    if self.explain_mode: self.trace.append(f"Short-circuit OR: {l} OR ... -> True")
                    return True
                r = self.eval_node(node.right)
                if self.explain_mode: self.trace.append(f"Evaluando: {l} OR {r} -> {bool(r)}")
                return bool(r)

            l, r = self.eval_node(node.left), self.eval_node(node.right)
            self.check_null(l, op); self.check_null(r, op)
            try:
                if op == "==": res = l == r
                elif op == "!=": res = l != r
                elif op == ">": res = l > r
                elif op == "<": res = l < r
                elif op == ">=": res = l >= r
                elif op == "<=": res = l <= r
                elif op == "+": res = l + r
                elif op == "-": res = l - r
                elif op == "*": res = l * r
                elif op == "/":
                    if r == 0: raise EvaluatorError("RF4001", "Division by zero")
                    res = l / r
            except TypeError as e: raise EvaluatorError("RF4002", f"Runtime Type Error: {e}")
            except InvalidOperation as e: raise EvaluatorError("RF4002", f"Decimal Runtime Error: {e}")
            if self.explain_mode: self.trace.append(f"Evaluando: {l} {op} {r} -> {res}")
            return res
        elif isinstance(node, FunctionCallNode):
            args = [self.eval_node(a) for a in node.args]
            try:
                if node.name == "contains": self.check_null(args[0], "contains"); res = args[1] in args[0]
                elif node.name == "length": self.check_null(args[0], "length"); res = len(args[0])
                elif node.name == "starts_with": self.check_null(args[0], "starts_with"); res = args[0].startswith(args[1])
                elif node.name == "ends_with": self.check_null(args[0], "ends_with"); res = args[0].endswith(args[1])
                elif node.name == "abs": self.check_null(args[0], "abs"); res = abs(args[0])
                else: raise EvaluatorError("RF4001", f"Unknown function {node.name}")
            except TypeError as e: raise EvaluatorError("RF4002", f"Runtime Type Error in '{node.name}': {e}")
            if self.explain_mode: self.trace.append(f"Evaluando función: {node.name}({args}) -> {res}")
            return res
        raise EvaluatorError("RF4001", f"Unknown AST node {type(node)}")
