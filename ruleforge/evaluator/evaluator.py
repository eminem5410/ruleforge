from ..parser.ast_nodes import RuleNode, ActionNode, BinaryOpNode, UnaryOpNode, NullCheckNode, LiteralNode, IdentifierNode, PropertyAccessNode, FunctionCallNode
from .errors import EvaluatorError

class Decision:
    def __init__(self, rule_name, lang_version, matched, actions, trace=None):
        self.rule_name = rule_name
        self.lang_version = lang_version
        self.matched = matched
        self.actions = actions
        self.trace = trace or []
    def __repr__(self): return f"Decision(rule='{self.rule_name}', matched={self.matched}, actions={self.actions})"

class Evaluator:
    def __init__(self, context, explain_mode=False):
        self.context = context
        self.explain_mode = explain_mode
        self.trace = []

    def eval_rules(self, ast_list):
        decisions = []
        for rule_node in ast_list:
            decisions.append(self.eval_rule(rule_node))
        return decisions

    def eval_rule(self, node: RuleNode):
        self.trace = []
        condition_result = self.eval_node(node.when_expr)
        if self.explain_mode:
            self.trace.append(f"CONDICIÓN FINAL EVALUADA COMO: {condition_result}")

        if condition_result:
            actions = node.then_actions
            matched = True
        else:
            actions = node.else_actions if node.else_actions else [ActionNode("NO_ACTION")]
            matched = False
            
        return Decision(node.name, node.lang_version, matched, actions, self.trace)

    def eval_node(self, node):
        if isinstance(node, LiteralNode):
            if node.type == "BOOLEAN": return node.value == "true"
            if node.type == "INTEGER": return int(node.value)
            if node.type == "DECIMAL": return float(node.value)
            if node.type == "DATE": return node.value # En V1, la fecha se maneja como string ISO para comparación léxica
            return node.value
            
        elif isinstance(node, PropertyAccessNode):
            obj = self.context.get(node.obj)
            if obj is None: return None
            return obj.get(node.prop)
            
        elif isinstance(node, NullCheckNode):
            val = self.eval_node(node.left)
            if node.is_not:
                result = val is not None; op_str = "IS NOT NULL"
            else:
                result = val is None; op_str = "IS NULL"
            if self.explain_mode: self.trace.append(f"Evaluando: {val} {op_str} -> {result}")
            return result
            
        elif isinstance(node, UnaryOpNode):
            val = self.eval_node(node.operand)
            if node.op == "NOT":
                result = not val
                if self.explain_mode: self.trace.append(f"Evaluando: NOT {val} -> {result}")
                return result
                
        elif isinstance(node, BinaryOpNode):
            left_val = self.eval_node(node.left)
            right_val = self.eval_node(node.right)
            op = node.op
            result = None
            
            if op == "AND": result = left_val and right_val
            elif op == "OR": result = left_val or right_val
            elif op == "==": result = left_val == right_val
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
                
            if self.explain_mode: self.trace.append(f"Evaluando: {left_val} {op} {right_val} -> {result}")
            return result
            
        elif isinstance(node, FunctionCallNode):
            args = [self.eval_node(arg) for arg in node.args]
            if node.name == "contains": result = args[1] in args[0]
            elif node.name == "length": result = len(args[0])
            elif node.name == "starts_with": result = args[0].startswith(args[1])
            elif node.name == "ends_with": result = args[0].endswith(args[1])
            elif node.name == "abs": result = abs(args[0])
            else: raise EvaluatorError("RF4001", f"Unknown function {node.name}")
            
            if self.explain_mode: self.trace.append(f"Evaluando función: {node.name}({args}) -> {result}")
            return result
            
        else:
            raise EvaluatorError("RF4001", f"Unknown AST node {type(node)}")
