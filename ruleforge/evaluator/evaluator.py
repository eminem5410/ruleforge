from datetime import date
from ..parser.ast_nodes import RuleNode, ActionNode, BinaryOpNode, UnaryOpNode, NullCheckNode, LiteralNode, IdentifierNode, PropertyAccessNode, FunctionCallNode
from .errors import EvaluatorError

class Decision:
    """
    Formal Decision Model. 
    This is the structured output of a RuleForge evaluation.
    """
    def __init__(self, rule_id, rule_version, language_version, matched, actions, trace=None):
        self.rule_id = rule_id
        self.rule_version = rule_version
        self.language_version = language_version
        self.matched = matched
        self.actions = actions
        self.trace = trace or []
        
    def __repr__(self): 
        return f"Decision(rule_id='{self.rule_id}', v{self.rule_version}, lang={self.language_version}, matched={self.matched}, actions={self.actions})"

class Evaluator:
    """
    RuleForge Evaluator.
    
    Contract: This component assumes the AST provided has already been 
    validated by the SemanticAnalyzer. It does not duplicate type checks.
    Its sole responsibility is to walk the AST and produce a Decision.
    """
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
            
        # rule_version asumo 1 por ahora hasta que implementemos metadata de reglas
        return Decision(node.name, 1, node.lang_version, matched, actions, self.trace)

    def eval_node(self, node):
        if isinstance(node, LiteralNode):
            if node.type == "BOOLEAN": return node.value == "true"
            if node.type == "INTEGER": return int(node.value)
            if node.type == "DECIMAL": return float(node.value)
            if node.type == "DATE": 
                y, m, d = map(int, node.value.split('-'))
                return date(y, m, d)
            return node.value
            
        elif isinstance(node, PropertyAccessNode):
            # Contrato: El Semantic Analyzer ya validó que la propiedad EXISTE en el Schema.
            # Si no está en el contexto de datos, lo tratamos como None para soportar IS NULL.
            obj = self.context.get(node.obj)
            if obj is None: return None
            return obj.get(node.prop)
            
        elif isinstance(node, IdentifierNode):
            return self.context.get(node.name)
            
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
            op = node.op
            
            # 1. Short-circuit AND
            if op == "AND":
                left_val = self.eval_node(node.left)
                if not left_val:
                    if self.explain_mode: self.trace.append(f"Short-circuit AND: {left_val} AND ... -> False")
                    return False
                right_val = self.eval_node(node.right)
                result = bool(right_val)
                if self.explain_mode: self.trace.append(f"Evaluando: {left_val} AND {right_val} -> {result}")
                return result
                
            # 2. Short-circuit OR
            elif op == "OR":
                left_val = self.eval_node(node.left)
                if left_val:
                    if self.explain_mode: self.trace.append(f"Short-circuit OR: {left_val} OR ... -> True")
                    return True
                right_val = self.eval_node(node.right)
                result = True if right_val else False
                if self.explain_mode: self.trace.append(f"Evaluando: {left_val} OR {right_val} -> {result}")
                return result

            # 3. Evaluación normal para el resto de operadores
            left_val = self.eval_node(node.left)
            right_val = self.eval_node(node.right)
            
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
