from ..parser.ast_nodes import RuleNode, ActionNode, BinaryOpNode, UnaryOpNode, NullCheckNode, LiteralNode, IdentifierNode, PropertyAccessNode, FunctionCallNode
from .errors import SemanticError

class SemanticAnalyzer:
    def __init__(self, context_schema):
        self.schema = context_schema
        # Fix abs: soporta Integer y Decimal
        self.functions = {
            "contains": (["String", "String"], "Boolean"),
            "length": (["String"], "Integer"),
            "starts_with": (["String", "String"], "Boolean"),
            "ends_with": (["String", "String"], "Boolean"),
            "abs": (["Numeric"], "Numeric")
        }

    def analyze(self, ast):
        for rule in ast:
            self.check_rule(rule)
        return True

    def check_rule(self, node):
        self.check_actions(node.then_actions)
        self.check_actions(node.else_actions)
        expr_type = self.check_node(node.when_expr)
        if expr_type != "Boolean":
            raise SemanticError("RF3002", f"WHEN condition must evaluate to Boolean, got {expr_type}")

    def check_actions(self, actions):
        terminal_count = sum(1 for a in actions if a.action_type in ["ALLOW", "DENY", "NO_ACTION"])
        if terminal_count > 1:
            raise SemanticError("RF3002", "A block can have at most ONE terminal decision")

    def check_node(self, node):
        if isinstance(node, LiteralNode):
            mapping = {"INTEGER": "Integer", "DECIMAL": "Decimal", "STRING": "String", "BOOLEAN": "Boolean", "DATE": "Date"}
            return mapping.get(node.type, "Unknown")
            
        elif isinstance(node, IdentifierNode):
            raise SemanticError("RF3002", f"Unknown context property '{node.name}'")
            
        elif isinstance(node, PropertyAccessNode):
            obj_schema = self.schema.get(node.obj)
            if not obj_schema:
                raise SemanticError("RF3002", f"Context object '{node.obj}' not defined in Schema")
            prop_type = obj_schema.get(node.prop)
            if not prop_type:
                raise SemanticError("RF3002", f"Property '{node.prop}' not found in '{node.obj}'")
            return prop_type
            
        elif isinstance(node, NullCheckNode):
            self.check_node(node.left)
            return "Boolean"
            
        elif isinstance(node, UnaryOpNode):
            if node.op == "NOT":
                operand_type = self.check_node(node.operand)
                if operand_type != "Boolean":
                    raise SemanticError("RF3001", f"Operator 'NOT' requires Boolean, got {operand_type}")
                return "Boolean"
            raise SemanticError("RF3001", f"Unknown unary operator {node.op}")
                
        elif isinstance(node, BinaryOpNode):
            left_type = self.check_node(node.left)
            right_type = self.check_node(node.right)
            op = node.op
            
            if op in ["AND", "OR"]:
                if left_type != "Boolean" or right_type != "Boolean":
                    raise SemanticError("RF3001", f"Operator '{op}' requires Boolean operands, got {left_type} and {right_type}")
                return "Boolean"
                
            elif op in ["==", "!="]:
                # Permitir Int/Dec, pero prohibir cruzar String/Bool/Date con números
                valid_numeric = ["Integer", "Decimal"]
                if (left_type in valid_numeric and right_type in valid_numeric):
                    return "Boolean"
                if left_type != right_type:
                    raise SemanticError("RF3001", f"Cannot compare {left_type} with {right_type} using '{op}'")
                return "Boolean"
                
            elif op in [">", "<", ">=", "<="]:
                valid_numeric = ["Integer", "Decimal"]
                if (left_type in valid_numeric and right_type in valid_numeric) or (left_type == "Date" and right_type == "Date"):
                    return "Boolean"
                raise SemanticError("RF3001", f"Operator '{op}' requires numeric/date operands, got {left_type} and {right_type}")
                
            elif op in ["+", "-", "*", "/"]:
                valid_numeric = ["Integer", "Decimal"]
                if left_type in valid_numeric and right_type in valid_numeric:
                    return "Decimal" if "Decimal" in [left_type, right_type] else "Integer"
                raise SemanticError("RF3001", f"Operator '{op}' requires numeric operands, got {left_type} and {right_type}")
            else:
                raise SemanticError("RF3001", f"Unknown operator {op}")
                
        elif isinstance(node, FunctionCallNode):
            if node.name not in self.functions:
                raise SemanticError("RF3003", f"Unknown function '{node.name}'")
            expected_args, return_type = self.functions[node.name]
            if len(node.args) != len(expected_args):
                raise SemanticError("RF3003", f"Function '{node.name}' expects {len(expected_args)} arguments, got {len(node.args)}")
            for i, arg_node in enumerate(node.args):
                arg_type = self.check_node(arg_node)
                # Fix para abs(Numeric)
                if expected_args[i] == "Numeric":
                    if arg_type not in ["Integer", "Decimal"]:
                        raise SemanticError("RF3003", f"Argument {i+1} of '{node.name}' must be Numeric, got {arg_type}")
                elif arg_type != expected_args[i]:
                    raise SemanticError("RF3003", f"Argument {i+1} of '{node.name}' must be {expected_args[i]}, got {arg_type}")
            return return_type
        else:
            raise SemanticError("RF3003", f"Unknown AST node {type(node)}")
