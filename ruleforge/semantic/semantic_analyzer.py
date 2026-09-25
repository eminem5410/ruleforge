from ..parser.ast_nodes import RuleNode, ActionNode, BinaryOpNode, UnaryOpNode, NullCheckNode, LiteralNode, IdentifierNode, PropertyAccessNode, FunctionCallNode
from .errors import SemanticError

MAX_AST_DEPTH = 50
MAX_AST_NODES = 500

class SemanticAnalyzer:
    def __init__(self, context_schema):
        self.schema = context_schema
        self.functions = {
            "contains": (["String", "String"], "Boolean"),
            "length": (["String"], "Integer"),
            "starts_with": (["String", "String"], "Boolean"),
            "ends_with": (["String", "String"], "Boolean"),
            "abs": (["Integer"], "Integer"), "abs": (["Numeric"], "Numeric")
        }

    def analyze(self, ast):
        for rule in ast:
            self.check_rule(rule)
        return True

    def check_rule(self, node):
        self.check_actions(node.then_actions)
        self.check_actions(node.else_actions)
        
        depth, count = self.check_ast_limits(node.when_expr, 1)
        if depth > MAX_AST_DEPTH:
            raise SemanticError("RF5001", f"Security Limit: AST depth {depth} exceeds maximum of {MAX_AST_DEPTH}")
        if count > MAX_AST_NODES:
            raise SemanticError("RF5002", f"Security Limit: AST node count {count} exceeds maximum of {MAX_AST_NODES}")
            
        expr_type = self.check_node(node.when_expr)
        if expr_type != "Boolean":
            raise SemanticError("RF3002", f"WHEN condition must evaluate to Boolean, got {expr_type}")

    def check_ast_limits(self, node, current_depth):
        count = 1
        if isinstance(node, BinaryOpNode):
            d1, c1 = self.check_ast_limits(node.left, current_depth + 1)
            d2, c2 = self.check_ast_limits(node.right, current_depth + 1)
            return max(d1, d2), count + c1 + c2
        elif isinstance(node, UnaryOpNode):
            d, c = self.check_ast_limits(node.operand, current_depth + 1)
            return d, count + c
        elif isinstance(node, NullCheckNode):
            d, c = self.check_ast_limits(node.left, current_depth + 1)
            return d, count + c
        elif isinstance(node, FunctionCallNode):
            max_d = current_depth
            for arg in node.args:
                d, c = self.check_ast_limits(arg, current_depth + 1)
                max_d = max(max_d, d)
                count += c
            return max_d, count
        return current_depth, count

    def check_actions(self, actions):
        terminal_count = sum(1 for a in actions if a.action_type in ["ALLOW", "DENY", "NO_ACTION"])
        if terminal_count > 1:
            raise SemanticError("RF3002", "A block can have at most ONE terminal decision")

    def check_node(self, node):
        if isinstance(node, LiteralNode): return {"INTEGER": "Integer", "DECIMAL": "Decimal", "STRING": "String", "BOOLEAN": "Boolean", "DATE": "Date"}.get(node.type, "Unknown")
        elif isinstance(node, IdentifierNode): raise SemanticError("RF3002", f"Unknown context property '{node.name}'")
        elif isinstance(node, PropertyAccessNode):
            obj_schema = self.schema.get(node.obj)
            if not obj_schema: raise SemanticError("RF3002", f"Context object '{node.obj}' not defined")
            prop_type = obj_schema.get(node.prop)
            if not prop_type: raise SemanticError("RF3002", f"Property '{node.prop}' not found in '{node.obj}'")
            return prop_type
        elif isinstance(node, NullCheckNode): self.check_node(node.left); return "Boolean"
        elif isinstance(node, UnaryOpNode):
            if node.op == "NOT":
                if self.check_node(node.operand) != "Boolean": raise SemanticError("RF3001", "Operator 'NOT' requires Boolean")
                return "Boolean"
        elif isinstance(node, BinaryOpNode):
            l, r, op = self.check_node(node.left), self.check_node(node.right), node.op
            if op in ["AND", "OR"]:
                if l != "Boolean" or r != "Boolean": raise SemanticError("RF3001", f"Operator '{op}' requires Boolean")
                return "Boolean"
            elif op in ["==", "!="]:
                if l != r: raise SemanticError("RF3001", f"Cannot compare {l} with {r}")
                return "Boolean"
            elif op in [">", "<", ">=", "<="]:
                if l not in ["Integer", "Decimal", "Date"] or r not in ["Integer", "Decimal", "Date"]: raise SemanticError("RF3001", f"Operator '{op}' requires numeric/date")
                return "Boolean"
            elif op in ["+", "-", "*", "/"]:
                if l not in ["Integer", "Decimal"] or r not in ["Integer", "Decimal"]: raise SemanticError("RF3001", f"Operator '{op}' requires numeric")
                return "Decimal" if "Decimal" in [l, r] else "Integer"
        elif isinstance(node, FunctionCallNode):
            if node.name not in self.functions: raise SemanticError("RF3003", f"Unknown function '{node.name}'")
            exp_args, ret = self.functions[node.name]
            if len(node.args) != len(exp_args): raise SemanticError("RF3003", f"Function '{node.name}' expects {len(exp_args)} arguments")
            for i, a in enumerate(node.args):
                t = self.check_node(a)
                if exp_args[i] == "Numeric":
                    if t not in ["Integer", "Decimal"]: raise SemanticError("RF3003", f"Argument {i+1} of '{node.name}' must be Numeric")
                elif t != exp_args[i]: raise SemanticError("RF3003", f"Argument {i+1} of '{node.name}' must be {exp_args[i]}")
            return ret
