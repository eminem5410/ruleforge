from decimal import Decimal
from ..evaluator import Evaluator
from ..evaluator.errors import EvaluatorError
from ..parser.ast_nodes import RuleNode, ActionNode, BinaryOpNode, UnaryOpNode, LiteralNode, PropertyAccessNode, EmitActionNode

def _safe_get(ctx, obj, prop):
    val = ctx.get(obj)
    if isinstance(val, dict): return val.get(prop)
    return None

class RuleForgeCompiler:
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
            if node.type == "DECIMAL": return f"Decimal({repr(node.value)})"
            if node.type == "BOOLEAN": return "True" if node.value == "true" else "False"
            raise NotImplementedError
            
        elif isinstance(node, PropertyAccessNode):
            return f"_safe_get(ctx, '{node.obj}', '{node.prop}')"
            
        elif isinstance(node, BinaryOpNode):
            if node.op in ["+", "-", "*", "/"]:
                left = self._compile_node(node.left)
                right = self._compile_node(node.right)
                return f"({left} {node.op} {right})"
                
            left = self._compile_node(node.left)
            right = self._compile_node(node.right)
            op = node.op
            if op == "AND": op = "and"
            elif op == "OR": op = "or"
            return f"({left} {op} {right})"
            
        elif isinstance(node, UnaryOpNode):
            if node.op == "NOT": return f"(not {self._compile_node(node.operand)})"
            raise NotImplementedError
            
        raise NotImplementedError

    def execute(self, context):
        evaluator = Evaluator(context)
        decisions = []
        globals_dict = {"__builtins__": {}, "_safe_get": _safe_get, "Decimal": Decimal}
        locals_dict = {"ctx": context}
        
        for rule in self.ast:
            code = self.compiled_conditions.get(id(rule))
            if code is None:
                decisions.append(evaluator.eval_rule(rule))
            else:
                try:
                    condition_result = bool(eval(code, globals_dict, locals_dict))
                except Exception:
                    # Fallback to interpreter for any runtime error (e.g. TypeError on float+Decimal, ZeroDivisionError)
                    decisions.append(evaluator.eval_rule(rule))
                    continue
                
                actions_to_resolve = rule.then_actions if condition_result else (rule.else_actions if rule.else_actions else [ActionNode("NO_ACTION")])
                resolved_actions = []
                
                for a in actions_to_resolve:
                    if isinstance(a, EmitActionNode):
                        payload = None
                        if a.payload_node:
                            payload, _ = evaluator.eval_node(a.payload_node)
                        resolved_actions.append(ActionNode("EMIT", a.value, payload))
                    else:
                        resolved_actions.append(a)
                
                decisions.append(evaluator.build_decision(rule, condition_result, resolved_actions))

        return decisions
