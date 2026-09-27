from ..parser.ast_nodes import RuleNode, ActionNode, BinaryOpNode, UnaryOpNode, NullCheckNode, LiteralNode, IdentifierNode, PropertyAccessNode, FunctionCallNode, ArrayLiteralNode, ArrayIndexNode, DateLiteralNode, EmitActionNode, SetActionNode
from .errors import SemanticError

MAX_AST_DEPTH = 50
MAX_AST_NODES = 500

class SemanticAnalyzer:
    def __init__(self, context_schema):
        self.schema = context_schema

    def analyze(self, ast):
        for rule in ast:
            self.check_rule(rule)
        return True

    def check_rule(self, node):
        for action in node.then_actions + node.else_actions:
            if isinstance(action, SetActionNode):
                obj_schema = self.schema.get(action.obj_name)
                if not obj_schema: raise SemanticError("RF3002", f"Context object '{action.obj_name}' not defined")
                prop_type = obj_schema.get(action.prop_name)
                if not prop_type: raise SemanticError("RF3002", f"Property '{action.prop_name}' not found in '{action.obj_name}'")
                val_type = self.check_node(action.value_node)
                if val_type != prop_type: raise SemanticError("RF3001", f"Cannot assign {val_type} to {prop_type}")
            if isinstance(action, EmitActionNode) and action.payload_node:
                # Only enforce that the context object exists. Missing properties are allowed and resolve to NULL.
                if isinstance(action.payload_node, PropertyAccessNode) and action.payload_node.obj not in self.schema:
                    raise SemanticError("RF3002", f"Context object '{action.payload_node.obj}' not defined")
                elif not isinstance(action.payload_node, PropertyAccessNode):
                    self.check_node(action.payload_node)
        self.check_actions(node.then_actions)
        self.check_actions(node.else_actions)
        
        depth, count = 0, 0
        self.check_ast_limits(node.when_expr, 1, depth, count)
        
        expr_type = self.check_node(node.when_expr)
        if expr_type != "Boolean":
            raise SemanticError("RF3002", f"WHEN condition must evaluate to Boolean, got {expr_type}")

    def check_ast_limits(self, node, current_depth, max_depth, count):
        count += 1
        if current_depth > max_depth: max_depth = current_depth
        if max_depth > MAX_AST_DEPTH: raise SemanticError("RF5001", f"Security Limit: AST depth exceeds maximum of {MAX_AST_DEPTH}")
        if count > MAX_AST_NODES: raise SemanticError("RF5002", f"Security Limit: AST node count exceeds maximum of {MAX_AST_NODES}")

        if isinstance(node, BinaryOpNode):
            self.check_ast_limits(node.left, current_depth + 1, max_depth, count)
            self.check_ast_limits(node.right, current_depth + 1, max_depth, count)
        elif isinstance(node, UnaryOpNode):
            self.check_ast_limits(node.operand, current_depth + 1, max_depth, count)
        elif isinstance(node, NullCheckNode):
            self.check_ast_limits(node.left, current_depth + 1, max_depth, count)
        elif isinstance(node, FunctionCallNode):
            for arg in node.args:
                self.check_ast_limits(arg, current_depth + 1, max_depth, count)
        elif isinstance(node, ArrayLiteralNode):
            for el in node.elements:
                self.check_ast_limits(el, current_depth + 1, max_depth, count)
        elif isinstance(node, ArrayIndexNode):
            self.check_ast_limits(node.array, current_depth + 1, max_depth, count)
            self.check_ast_limits(node.index, current_depth + 1, max_depth, count)

    def check_actions(self, actions):
        terminal_count = sum(1 for a in actions if a.action_type in ["ALLOW", "DENY", "NO_ACTION"])
        if terminal_count > 1:
            raise SemanticError("RF3002", "A block can have at most ONE terminal decision")

    def check_node(self, node):
        if isinstance(node, LiteralNode):
            mapping = {"INTEGER": "Integer", "DECIMAL": "Decimal", "STRING": "String", "BOOLEAN": "Boolean", "DATE": "Date"}
            return mapping.get(node.type, "Unknown")
        if isinstance(node, DateLiteralNode):
            return "Date"
            
        elif isinstance(node, IdentifierNode):
            raise SemanticError("RF3002", f"Unknown context property '{node.name}'")
            
        elif isinstance(node, PropertyAccessNode):
            obj_schema = self.schema.get(node.obj)
            if not obj_schema: raise SemanticError("RF3002", f"Context object '{node.obj}' not defined")
            prop_type = obj_schema.get(node.prop)
            if not prop_type: raise SemanticError("RF3002", f"Property '{node.prop}' not found in '{node.obj}'")
            return prop_type
            
        elif isinstance(node, NullCheckNode):
            self.check_node(node.left)
            return "Boolean"
            
        elif isinstance(node, UnaryOpNode):
            if node.op == "NOT":
                if self.check_node(node.operand) != "Boolean":
                    raise SemanticError("RF3001", "Operator 'NOT' requires Boolean")
                return "Boolean"
                
        elif isinstance(node, BinaryOpNode):
            left_type = self.check_node(node.left)
            right_type = self.check_node(node.right)
            op = node.op
            
            valid_numerics = ["Integer", "Decimal"]
            valid_comparison = ["Integer", "Decimal", "Date"]
            
            if op in ["AND", "OR"]:
                if left_type != "Boolean" or right_type != "Boolean": raise SemanticError("RF3001", f"Operator '{op}' requires Boolean operands")
                return "Boolean"
            elif op in ["==", "!="]:
                # Allow comparison between Integer and Decimal (Numeric types)
                if left_type in valid_numerics and right_type in valid_numerics:
                    return "Boolean"
                if left_type != right_type: raise SemanticError("RF3001", f"Cannot compare {left_type} with {right_type}")
                return "Boolean"
            elif op in [">", "<", ">=", "<="]:
                if left_type not in valid_comparison or right_type not in valid_comparison: raise SemanticError("RF3001", f"Operator '{op}' requires numeric/date")
                return "Boolean"
            elif op in ["+", "-", "*", "/"]:
                if op == "+" and left_type == "String" and right_type == "String":
                    return "String"
                if left_type not in valid_numerics or right_type not in valid_numerics: raise SemanticError("RF3001", f"Operator '{op}' requires numeric or String operands")
                if op == "/": return "Decimal" # Division always yields Decimal
                return "Decimal" if "Decimal" in [left_type, right_type] else "Integer"

        elif isinstance(node, ArrayLiteralNode):
            if not node.elements:
                return "Array<Null>"
            types = [self.check_node(el) for el in node.elements]
            first_type = types[0]
            for t in types[1:]:
                if t != first_type:
                    raise SemanticError("RF3003", f"Heterogeneous array literal. Expected {first_type}, got {t}")
            return f"Array<{first_type}>"
            
        elif isinstance(node, ArrayIndexNode):
            arr_type = self.check_node(node.array)
            idx_type = self.check_node(node.index)
            if idx_type != "Integer":
                raise SemanticError("RF3003", f"Array index must be Integer, got {idx_type}")
            if not arr_type.startswith("Array<"):
                raise SemanticError("RF3003", f"Cannot index non-array type {arr_type}")
            inner_type = arr_type[6:-1]
            return inner_type

        elif isinstance(node, FunctionCallNode):
            func_name = node.name.lower()
            if func_name not in ["contains", "length", "starts_with", "ends_with", "abs", "date_add", "date_diff", "extract"]:
                raise SemanticError("RF3003", f"Unknown function '{node.name}'")
                
            if func_name == "length":
                if len(node.args) != 1: raise SemanticError("RF3003", "Function 'length' expects 1 argument")
                arg_type = self.check_node(node.args[0])
                if arg_type != "String" and not arg_type.startswith("Array<"):
                    raise SemanticError("RF3003", f"Function 'length' expects a String or Array, got {arg_type}")
                return "Integer"
                
            elif func_name == "date_add":
                if len(node.args) != 2: raise SemanticError("RF3003", "Function 'date_add' expects 2 arguments")
                arg1_type = self.check_node(node.args[0])
                arg2_type = self.check_node(node.args[1])
                if arg1_type != "Date": raise SemanticError("RF3003", f"Argument 1 of 'date_add' must be Date, got {arg1_type}")
                if arg2_type != "Integer": raise SemanticError("RF3003", f"Argument 2 of 'date_add' must be Integer, got {arg2_type}")
                return "Date"
            elif func_name == "date_diff":
                if len(node.args) != 2: raise SemanticError("RF3003", "Function 'date_diff' expects 2 arguments")
                arg1_type = self.check_node(node.args[0])
                arg2_type = self.check_node(node.args[1])
                if arg1_type != "Date" or arg2_type != "Date": raise SemanticError("RF3003", "Function 'date_diff' requires Date arguments")
                return "Integer"
            elif func_name == "extract":
                if len(node.args) != 2: raise SemanticError("RF3003", "Function 'extract' expects 2 arguments")
                arg1_type = self.check_node(node.args[0])
                if arg1_type != "Date": raise SemanticError("RF3003", f"Argument 1 of 'extract' must be Date, got {arg1_type}")
                if not isinstance(node.args[1], LiteralNode) or node.args[1].type != "STRING":
                    raise SemanticError("RF3003", "Argument 2 of 'extract' must be String literal")
                part = node.args[1].value
                if part not in ["year", "month", "day"]: raise SemanticError("RF3003", f"Invalid part for EXTRACT. Expected 'year', 'month', or 'day'")
                return "Integer"
            elif func_name == "contains":
                if len(node.args) != 2: raise SemanticError("RF3003", "Function 'contains' expects 2 arguments")
                arg1_type = self.check_node(node.args[0])
                arg2_type = self.check_node(node.args[1])
                
                if arg1_type == "String":
                    if arg2_type != "String": raise SemanticError("RF3003", f"Argument 2 of 'contains' must be String, got {arg2_type}")
                elif arg1_type.startswith("Array<"):
                    inner_type = arg1_type[6:-1]
                    if inner_type == "Null":
                        raise SemanticError("RF3003", "Cannot infer array type from empty array literal in 'contains'")
                    if inner_type != arg2_type:
                        raise SemanticError("RF3003", f"Argument 2 of 'contains' must be {inner_type}, got {arg2_type}")
                else:
                    raise SemanticError("RF3003", f"Function 'contains' expects a String or Array as first argument, got {arg1_type}")
                return "Boolean"
                
            elif func_name in ["starts_with", "ends_with"]:
                if len(node.args) != 2: raise SemanticError("RF3003", f"Function '{func_name}' expects 2 arguments")
                t1 = self.check_node(node.args[0])
                t2 = self.check_node(node.args[1])
                if t1 != "String" or t2 != "String": raise SemanticError("RF3003", f"Function '{func_name}' requires String arguments")
                return "Boolean"
            elif func_name == "abs":
                if len(node.args) != 1: raise SemanticError("RF3003", "Function 'abs' expects 1 argument")
                t = self.check_node(node.args[0])
                if t not in ["Integer", "Decimal"]: raise SemanticError("RF3003", "Function 'abs' requires Numeric argument")
                return t

        raise SemanticError("RF3003", "Unknown AST node")
