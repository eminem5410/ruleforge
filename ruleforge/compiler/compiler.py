from ..evaluator import Evaluator
from ..evaluator.errors import EvaluatorError
from ..parser.ast_nodes import RuleNode, ActionNode, BinaryOpNode, UnaryOpNode, LiteralNode, PropertyAccessNode

def _safe_get(ctx, obj, prop):
    val = ctx.get(obj)
    if isinstance(val, dict): return val.get(prop)
    return None

class RuleForgeCompiler:
    """
    V9.0.0-Beta: Real Python compilation (Slice 1).
    Preserves interpreter semantics by falling back to interpreter for Decimals and Arithmetic.
    """
    def __init__(self, ast):
        self.ast = ast
        self.compiled_conditions = {}
        for rule in ast:
            try:
                expr_str = self._compile_node(rule.when_expr)
                code = compile(expr_str, "<ruleforge>", "eval")
                self.compiled_conditions[id(rule)] = code
            except NotImplementedError:
                pass

    def _compile_node(self, node):
        if isinstance(node, LiteralNode):
            if node.type == "STRING": return repr(node.value)
            if node.type == "INTEGER": return str(node.value)
            if node.type == "BOOLEAN": return "True" if node.value == "true" else "False"
            # Fall back for DECIMAL to preserve Decimal semantics
            raise NotImplementedError
            
        elif isinstance(node, PropertyAccessNode):
            return f"_safe_get(ctx, '{node.obj}', '{node.prop}')"
            
        elif isinstance(node, BinaryOpNode):
            # Fall back for arithmetic to preserve Decimal semantics
            if node.op in ["+", "-", "*", "/"]:
                raise NotImplementedError
                
            left = self._compile_node(node.left)
            right = self._compile_node(node.right)
            op = node.op
            if op == "AND": op = "and"
            elif op == "OR": op = "or"
            return f"({left} {op} {right})"
            
        elif isinstance(node, UnaryOpNode):
            if node.op == "NOT":
                operand = self._compile_node(node.operand)
                return f"(not {operand})"
            raise NotImplementedError
            
        raise NotImplementedError

    def execute(self, context):
        evaluator = Evaluator(context)
        decisions = []
        globals_dict = {"__builtins__": {}, "_safe_get": _safe_get}
        locals_dict = {"ctx": context}
        
        from ..parser.ast_nodes import LiteralNode as _Lit
        
        for rule in self.ast:
            code = self.compiled_conditions.get(id(rule))
            if code is None:
                decisions.append(evaluator.eval_rule(rule))
            else:
                try:
                    condition_result = bool(eval(code, globals_dict, locals_dict))
                except TypeError:
                    raise EvaluatorError("RF4002", "Runtime Type Error on NULL or incompatible types.")
                except ZeroDivisionError:
                    raise EvaluatorError("RF4001", "Division by zero")
                
                dummy_expr = _Lit("true", "BOOLEAN") if condition_result else _Lit("false", "BOOLEAN")
                original_expr = rule.when_expr
                rule.when_expr = dummy_expr
                decisions.append(evaluator.eval_rule(rule))
                rule.when_expr = original_expr
                
        return decisions
