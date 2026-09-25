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
        self.context, self.explain_mode = context, explain_mode
        self.trace = []
        self.step_count = 0

    def eval_rules(self, ast_list):
        return [self.eval_rule(rule) for rule in ast_list]

    def eval_rule(self, node: RuleNode):
        self.step_count = 0
        self.trace = []
        try:
            condition_result, root_trace = self.eval_node(node.when_expr)
        except EvaluatorError: raise
        except Exception as e:
            raise EvaluatorError("RF4001", f"Unexpected runtime error: {e}")
            
        if self.explain_mode: 
            self.trace = [root_trace]
            
        actions = node.then_actions if condition_result else (node.else_actions if node.else_actions else [ActionNode("NO_ACTION")])
        return Decision(node.name, 1, node.lang_version, condition_result, actions, self.trace)

    def check_null(self, val, op):
        if val is None: raise EvaluatorError("RF4002", f"Runtime Type Error: Cannot perform '{op}' on NULL. Use IS NULL / IS NOT NULL.")

    def eval_node(self, node):
        self.step_count += 1
        if self.step_count > MAX_EXECUTION_STEPS:
            raise EvaluatorError("RF5003", f"Security Limit: Execution exceeded {MAX_EXECUTION_STEPS} steps")

        if isinstance(node, LiteralNode):
            val = None
            if node.type == "BOOLEAN": val = node.value == "true"
            elif node.type == "INTEGER": val = int(node.value)
            elif node.type == "DECIMAL": val = Decimal(node.value)
            elif node.type == "DATE": y, m, d = map(int, node.value.split('-')); val = date(y, m, d)
            else: val = node.value
            
            if self.explain_mode:
                data_type = {"INTEGER": "Integer", "DECIMAL": "Decimal", "STRING": "String", "BOOLEAN": "Boolean", "DATE": "Date"}.get(node.type, "Unknown")
                return val, {"type": "literal", "value": val, "data_type": data_type}
            return val, None
            
        elif isinstance(node, PropertyAccessNode):
            obj = self.context.get(node.obj)
            val = normalize_value(obj.get(node.prop)) if obj else None
            if self.explain_mode:
                return val, {"type": "property", "path": f"{node.obj}.{node.prop}", "value": val}
            return val, None
            
        elif isinstance(node, IdentifierNode):
            val = normalize_value(self.context.get(node.name))
            if self.explain_mode:
                return val, {"type": "property", "path": node.name, "value": val}
            return val, None
            
        elif isinstance(node, NullCheckNode):
            val, left_trace = self.eval_node(node.left)
            result = val is not None if node.is_not else val is None
            op_str = "IS NOT NULL" if node.is_not else "IS NULL"
            if self.explain_mode:
                return result, {"type": "null_check", "operator": op_str, "value": left_trace, "result": result}
            return result, None
            
        elif isinstance(node, UnaryOpNode):
            val, operand_trace = self.eval_node(node.operand)
            if node.op == "NOT":
                self.check_null(val, "NOT")
                result = not val
                if self.explain_mode:
                    return result, {"type": "unary", "operator": "NOT", "operand": operand_trace, "result": result}
                return result, None
                
        elif isinstance(node, BinaryOpNode):
            op = node.op
            if op == "AND":
                left_val, left_trace = self.eval_node(node.left)
                if not left_val:
                    if self.explain_mode:
                        return False, {"type": "short_circuit", "operator": "AND", "left": left_trace, "result": False}
                    return False, None
                right_val, right_trace = self.eval_node(node.right)
                result = bool(right_val)
                if self.explain_mode:
                    return result, {"type": "logical", "operator": "AND", "left": left_trace, "right": right_trace, "result": result}
                return result, None
                
            elif op == "OR":
                left_val, left_trace = self.eval_node(node.left)
                if left_val:
                    if self.explain_mode:
                        return True, {"type": "short_circuit", "operator": "OR", "left": left_trace, "result": True}
                    return True, None
                right_val, right_trace = self.eval_node(node.right)
                result = True if right_val else False
                if self.explain_mode:
                    return result, {"type": "logical", "operator": "OR", "left": left_trace, "right": right_trace, "result": result}
                return result, None

            left_val, left_trace = self.eval_node(node.left)
            right_val, right_trace = self.eval_node(node.right)
            self.check_null(left_val, op); self.check_null(right_val, op)
            try:
                if op == "==": res = left_val == right_val
                elif op == "!=": res = left_val != right_val
                elif op == ">": res = left_val > right_val
                elif op == "<": res = left_val < right_val
                elif op == ">=": res = left_val >= right_val
                elif op == "<=": res = left_val <= right_val
                elif op == "+": res = left_val + right_val
                elif op == "-": res = left_val - right_val
                elif op == "*": res = left_val * right_val
                elif op == "/":
                    if right_val == 0: raise EvaluatorError("RF4001", "Division by zero")
                    res = left_val / right_val
            except TypeError as e: raise EvaluatorError("RF4002", f"Runtime Type Error: {e}")
            except InvalidOperation as e: raise EvaluatorError("RF4002", f"Decimal Runtime Error: {e}")
            
            if self.explain_mode:
                if op in ["==", "!=", ">", "<", ">=", "<="]:
                    return res, {"type": "comparison", "operator": op, "left": left_trace, "right": right_trace, "result": res}
                else:
                    return res, {"type": "arithmetic", "operator": op, "left": left_trace, "right": right_trace, "result": res}
            return res, None
            
        elif isinstance(node, FunctionCallNode):
            arg_vals = []
            arg_traces = []
            for a in node.args:
                v, t = self.eval_node(a)
                arg_vals.append(v)
                arg_traces.append(t)
                
            try:
                if node.name == "contains": self.check_null(arg_vals[0], "contains"); res = arg_vals[1] in arg_vals[0]
                elif node.name == "length": self.check_null(arg_vals[0], "length"); res = len(arg_vals[0])
                elif node.name == "starts_with": self.check_null(arg_vals[0], "starts_with"); res = arg_vals[0].startswith(arg_vals[1])
                elif node.name == "ends_with": self.check_null(arg_vals[0], "ends_with"); res = arg_vals[0].endswith(arg_vals[1])
                elif node.name == "abs": self.check_null(arg_vals[0], "abs"); res = abs(arg_vals[0])
                else: raise EvaluatorError("RF4001", f"Unknown function {node.name}")
            except TypeError as e: raise EvaluatorError("RF4002", f"Runtime Type Error in '{node.name}': {e}")
            
            if self.explain_mode:
                return res, {"type": "function", "name": node.name, "arguments": arg_traces, "result": res}
            return res, None
            
        raise EvaluatorError("RF4001", f"Unknown AST node {type(node)}")
