from .ast_nodes import *

class SemanticAnalyzer:
    def __init__(self, context_schema):
        self.schema=context_schema
        self.functions={"contains":(["String","String"],"Boolean"),"length":(["String"],"Integer"),"abs":(["Integer"],"Integer")}
    def analyze(self, ast):
        expr_type=self.check_node(ast.when_expr)
        if expr_type!="Boolean": raise Exception(f"RF3002 Semantic Error: WHEN condition must evaluate to Boolean, but evaluated to {expr_type}")
        return True
    def check_node(self, node):
        if isinstance(node, LiteralNode): return {"INTEGER":"Integer","DECIMAL":"Decimal","STRING":"String","BOOLEAN":"Boolean"}.get(node.type,"Unknown")
        elif isinstance(node, PropertyAccessNode):
            obj_schema=self.schema.get(node.obj)
            if not obj_schema: raise Exception(f"RF3002 Context Error: Object '{node.obj}' not defined")
            prop_type=obj_schema.get(node.prop)
            if not prop_type: raise Exception(f"RF3002 Context Error: Property '{node.prop}' not found in '{node.obj}'")
            return prop_type
        elif isinstance(node, NullCheckNode): self.check_node(node.left); return "Boolean"
        elif isinstance(node, BinaryOpNode):
            left_type=self.check_node(node.left); right_type=self.check_node(node.right); op=node.op
            if op in ["AND","OR"]:
                if left_type!="Boolean" or right_type!="Boolean": raise Exception(f"RF3001 Type Error: Operator '{op}' requires Boolean operands")
                return "Boolean"
            elif op in ["==","!="]:
                if left_type!=right_type: raise Exception(f"RF3001 Type Error: Cannot compare {left_type} with {right_type}")
                return "Boolean"
            elif op in [">","<",">=","<="]:
                if left_type not in ["Integer","Decimal"] or right_type not in ["Integer","Decimal"]: raise Exception(f"RF3001 Type Error: Operator '{op}' requires numeric operands")
                return "Boolean"
            elif op in ["+","-","*","/"]:
                if left_type not in ["Integer","Decimal"] or right_type not in ["Integer","Decimal"]: raise Exception(f"RF3001 Type Error: Operator '{op}' requires numeric operands")
                return "Decimal" if "Decimal" in [left_type,right_type] else "Integer"
        elif isinstance(node, FunctionCallNode):
            if node.name not in self.functions: raise Exception(f"RF3003 Semantic Error: Unknown function '{node.name}'")
            expected_args,return_type=self.functions[node.name]
            if len(node.args)!=len(expected_args): raise Exception(f"RF3003 Semantic Error: Function '{node.name}' expects {len(expected_args)} arguments")
            for i,arg_node in enumerate(node.args):
                if self.check_node(arg_node)!=expected_args[i]: raise Exception(f"RF3003 Semantic Error: Argument {i+1} of '{node.name}' must be {expected_args[i]}")
            return return_type
