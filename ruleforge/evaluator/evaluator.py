from decimal import Decimal, InvalidOperation
from datetime import date
from ..parser.ast_nodes import RuleNode, ActionNode, BinaryOpNode, UnaryOpNode, NullCheckNode, LiteralNode, IdentifierNode, PropertyAccessNode, FunctionCallNode
from .errors import EvaluatorError

class Decision:
    def __init__(self, rule_id, rule_version, language_version, matched, actions, trace=None):
        self.rule_id = rule_id
        self.rule_version = rule_version
        self.language_version = language_version
        self.matched = matched
        self.actions = actions
        self.trace = trace or []
    def __repr__(self): return f"Decision(rule_id='{self.rule_id}', matched={self.matched})"
    def to_dict(self):
        return {
            "rule_id": self.rule_id,
            "rule_version": self.rule_version,
            "language_version": self.language_version,
            "matched": self.matched,
            "actions": [a.to_dict() for a in self.actions],
            "trace": self.trace
        }

class Evaluator:
    def __init__(self, context, explain_mode=False):
        self.context = context
        self.explain_mode = explain_mode
        self.trace = []

    def eval_rules(self, ast_list):
        return [self.eval_rule(rule) for rule in ast_list]

    def eval_rule(self, node: RuleNode):
        self.trace = []
        try:
            condition_result = self.eval_node(node.when_expr)
        except EvaluatorError:
            raise
        except Exception as e:
            raise EvaluatorError("RF4001", f"Unexpected runtime error during evaluation: {e}")
            
        if self.explain_mode: self.trace.append(f"CONDICIÓN FINAL EVALUADA COMO: {condition_result}")

        if condition_result:
            actions = node.then_actions; matched = True
        else:
            actions = node.else_actions if node.else_actions else [ActionNode("NO_ACTION")]; matched = False
        return Decision(node.name, 1, node.lang_version, matched, actions, self.trace)

    def check_null(self, val, op):
        if val is None:
            raise EvaluatorError("RF4002", f"Runtime Type Error: Cannot perform '{op}' on NULL value. Use IS NULL / IS NOT NULL.")

    def eval_node(self, node):
        if isinstance(node, LiteralNode):
            if node.type == "BOOLEAN": return node.value == "true"
            if node.type == "INTEGER": return int(node.value)
            if node.type == "DECIMAL": return Decimal(node.value)
            if node.type == "DATE": 
                y, m, d = map(int, node.value.split('-')); return date(y, m, d)
            return node.value
            
        elif isinstance(node, PropertyAccessNode):
            obj = self.context.get(node.obj)
            if obj is None: return None
            return obj.get(node.prop)
            
        elif isinstance(node, IdentifierNode):
            return self.context.get(node.name)
            
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
                left_val = self.eval_node(node.left)
                if not left_val:
                    if self.explain_mode: self.trace.append(f"Short-circuit AND: {left_val} AND ... -> False")
                    return False
                right_val = self.eval_node(node.right)
                result = bool(right_val)
                if self.explain_mode: self.trace.append(f"Evaluando: {left_val} AND {right_val} -> {result}")
                return result
            elif op == "OR":
                left_val = self.eval_node(node.left)
                if left_val:
                    if self.explain_mode: self.trace.append(f"Short-circuit OR: {left_val} OR ... -> True")
                    return True
                right_val = self.eval_node(node.right)
                result = True if right_val else False
                if self.explain_mode: self.trace.append(f"Evaluando: {left_val} OR {right_val} -> {result}")
                return result

            left_val = self.eval_node(node.left)
            right_val = self.eval_node(node.right)
            
            self.check_null(left_val, op)
            self.check_null(right_val, op)
            
            try:
                result = None
                if op == "==": result = left_val == right_val
                elif op == "!=": result = left_val != right_val
                elif op == ">": result = left_val > right_val
                elif op == "<": result = left_val < right_val
                elif op == ">=": result = left_val >= right_val
                elif op == "<=": result = left_val <= right_val
                elif op == "+": result = left_val + right_val
                elif op == "-": result = left_val - right_val
                elif op == "*": result = left_val * right_val
                elif op == "/": 
                    if right_val == 0: raise EvaluatorError("RF4001", "Division by zero")
                    result = left_val / right_val
            except TypeError as e:
                raise EvaluatorError("RF4002", f"Runtime Type Error: {e}")
            except InvalidOperation as e:
                raise EvaluatorError("RF4002", f"Decimal Runtime Error: {e}")
                
            if self.explain_mode: self.trace.append(f"Evaluando: {left_val} {op} {right_val} -> {result}")
            return result
            
        elif isinstance(node, FunctionCallNode):
            args = [self.eval_node(arg) for arg in node.args]
            try:
                if node.name == "contains":
                    self.check_null(args[0], "contains")
                    result = args[1] in args[0]
                elif node.name == "length":
                    self.check_null(args[0], "length")
                    result = len(args[0])
                elif node.name == "starts_with":
                    self.check_null(args[0], "starts_with")
                    result = args[0].startswith(args[1])
                elif node.name == "ends_with":
                    self.check_null(args[0], "ends_with")
                    result = args[0].endswith(args[1])
                elif node.name == "abs":
                    self.check_null(args[0], "abs")
                    result = abs(args[0])
                else:
                    raise EvaluatorError("RF4001", f"Unknown function {node.name}")
            except TypeError as e:
                raise EvaluatorError("RF4002", f"Runtime Type Error in function '{node.name}': {e}")
                
            if self.explain_mode: self.trace.append(f"Evaluando función: {node.name}({args}) -> {result}")
            return result
        else:
            raise EvaluatorError("RF4001", f"Unknown AST node {type(node)}")
