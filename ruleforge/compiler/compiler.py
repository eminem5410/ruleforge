from decimal import Decimal
from datetime import date, timedelta
from ..evaluator import Evaluator
from ..evaluator.errors import EvaluatorError
from ..parser.ast_nodes import RuleNode, ActionNode, BinaryOpNode, UnaryOpNode, LiteralNode, PropertyAccessNode, EmitActionNode, FunctionCallNode, NullCheckNode, DateLiteralNode, ArrayLiteralNode, ArrayIndexNode, SetActionNode, AnyAllNode, FilterMapNode

def _safe_index(arr, idx):
    if arr is None or not isinstance(arr, list): raise EvaluatorError("RF4002", "Cannot index non-array")
    if idx < 0 or idx >= len(arr): raise EvaluatorError("RF4002", f"Array index out of bounds: {idx}")
    return arr[idx]

def _safe_get(ctx, obj, prop):
    val = ctx.get(obj)
    if isinstance(val, dict): return val.get(prop)
    return None

def _get_date(val):
    if isinstance(val, date): return val
    if isinstance(val, str):
        try:
            parts = val.split("-")
            return date(int(parts[0]), int(parts[1]), int(parts[2]))
        except (ValueError, IndexError):
            raise EvaluatorError("RF4002", "Invalid date format")
    raise EvaluatorError("RF4002", "Value is not a date")

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

        elif isinstance(node, DateLiteralNode):
            # node.value is already a datetime.date object from the parser
            return f"date({node.value.year}, {node.value.month}, {node.value.day})"

        elif isinstance(node, PropertyAccessNode):
            return f"_safe_get(ctx, '{node.obj}', '{node.prop}')"

        elif isinstance(node, FunctionCallNode):
            name = node.name.lower()
            if name == "length" and len(node.args) == 1:
                return f"len({self._compile_node(node.args[0])})"
            elif name == "contains" and len(node.args) == 2:
                return f"({self._compile_node(node.args[1])} in {self._compile_node(node.args[0])})"
            elif name == "date_add" and len(node.args) == 2:
                return f"(_get_date({self._compile_node(node.args[0])}) + timedelta(days={self._compile_node(node.args[1])}))"
            elif name == "date_diff" and len(node.args) == 2:
                return f"((_get_date({self._compile_node(node.args[1])}) - _get_date({self._compile_node(node.args[0])})).days)"
            elif name == "extract" and len(node.args) == 2:
                if not isinstance(node.args[1], LiteralNode) or node.args[1].type != "STRING": raise NotImplementedError
                part = node.args[1].value
                if part not in ["year", "month", "day"]: raise NotImplementedError
                return f"getattr(_get_date({self._compile_node(node.args[0])}), '{part}')"
            raise NotImplementedError

        elif isinstance(node, ArrayLiteralNode):
            elements = [self._compile_node(el) for el in node.elements]
            return "[" + ", ".join(elements) + "]"

        elif isinstance(node, ArrayIndexNode):
            arr = self._compile_node(node.array)
            idx = self._compile_node(node.index)
            return f"_safe_index({arr}, {idx})"

        elif isinstance(node, NullCheckNode):
            operand = self._compile_node(node.left)
            return f"({operand} is not None)" if node.is_not else f"({operand} is None)"

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

    def _resolve_actions(self, rule, condition_result, evaluator):
        """Resolve acciones de una regla compilada manteniendo la semántica del Evaluator."""
        try:
            actions_to_resolve = (
                rule.then_actions
                if condition_result
                else (rule.else_actions if rule.else_actions else [ActionNode("NO_ACTION")])
            )

            resolved_actions = []

            for action in actions_to_resolve:
                if isinstance(action, SetActionNode):
                    val, _ = evaluator.eval_node(action.value_node)
                    resolved_actions.append(ActionNode("SET", action.value, val))
                elif isinstance(action, EmitActionNode):
                    payload = None
                    if action.payload_node:
                        payload, _ = evaluator.eval_node(action.payload_node)
                    resolved_actions.append(ActionNode("EMIT", action.value, payload))
                else:
                    resolved_actions.append(action)

            return resolved_actions

        except EvaluatorError:
            raise
        except Exception as e:
            raise EvaluatorError("RF4001", f"Unexpected runtime error in action: {e}")

    def _execute_compiled_rule(self, rule, context, evaluator=None):
        """Ejecuta una regla compilada sin reevaluar el pipeline completo."""
        evaluator = evaluator or Evaluator(context)

        globals_dict = {
            "__builtins__": {},
            "_safe_get": _safe_get,
            "_safe_index": _safe_index,
            "Decimal": Decimal,
            "date": date,
            "timedelta": timedelta,
            "_get_date": _get_date,
        }
        locals_dict = {"ctx": context}

        code = self.compiled_conditions.get(id(rule))
        if code is None:
            return evaluator.eval_rule(rule)

        try:
            condition_result = bool(eval(code, globals_dict, locals_dict))
        except Exception:
            return evaluator.eval_rule(rule)

        resolved_actions = self._resolve_actions(
            rule,
            condition_result,
            evaluator,
        )

        return evaluator.build_decision(
            rule,
            condition_result,
            resolved_actions,
        )

    def execute_single(self, rule, context):
        """Evalúa una sola regla sin reevaluar el pipeline completo."""
        return self._execute_compiled_rule(rule, context)

    def execute(self, context):
        evaluator = Evaluator(context)
        decisions = []

        for rule in self.ast:
            decisions.append(
                self._execute_compiled_rule(
                    rule,
                    context,
                    evaluator,
                )
            )

        return decisions
