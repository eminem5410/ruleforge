from decimal import Decimal, InvalidOperation
from datetime import date, timedelta
from ..parser.ast_nodes import (RuleNode, ActionNode, BinaryOpNode, UnaryOpNode,
    NullCheckNode, LiteralNode, IdentifierNode, PropertyAccessNode,
    FunctionCallNode, ArrayLiteralNode, ArrayIndexNode, DateLiteralNode,
    EmitActionNode, SetActionNode, AnyAllNode, FilterMapNode)
from .errors import EvaluatorError

MAX_EXECUTION_STEPS = 10000

# V11.2: Canonical NodeType mapping. Must match C# exactly.
# No silent fallback: unmapped node types raise RF5004.
NODE_TYPE_MAP = {
    BinaryOpNode: "BinaryExpression",
    UnaryOpNode: "UnaryExpression",
    NullCheckNode: "NullCheck",
    LiteralNode: "Literal",
    IdentifierNode: "Identifier",
    PropertyAccessNode: "PropertyExpression",
    FunctionCallNode: "FunctionCall",
    ArrayLiteralNode: "ArrayLiteral",
    ArrayIndexNode: "ArrayIndex",
    DateLiteralNode: "DateLiteral",
    AnyAllNode: "AnyAll",
    FilterMapNode: "FilterMap",
}

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
    def __init__(self, context, deep_trace=False):
        self.context = context
        self.deep_trace = deep_trace
        self.trace = []
        self.step_count = 0
        self._error_trace = None

    def eval_rules(self, ast_list):
        return [self.eval_rule(rule) for rule in ast_list]

    def build_decision(self, node, matched, actions):
        return Decision(node.name, 1, node.lang_version, matched, actions)

    # ─── V11.2 Trace Helpers ───────────────────────────────────

    def _node_type(self, node):
        t = type(node)
        if t not in NODE_TYPE_MAP:
            raise EvaluatorError("RF5004", f"V11.2: Unmapped AST node type {t.__name__}")
        return NODE_TYPE_MAP[t]

    def _value_type(self, val):
        if val is None: return "Null"
        if isinstance(val, bool): return "Boolean"
        if isinstance(val, int): return "Integer"
        if isinstance(val, Decimal): return "Decimal"
        if isinstance(val, str): return "String"
        if isinstance(val, date): return "Date"
        if isinstance(val, list): return "Array"
        if isinstance(val, dict): return "Object"
        return "Unknown"

    def _serialize_value(self, val):
        if isinstance(val, date): return val.isoformat()
        if isinstance(val, Decimal): return str(val)
        return val

    def _mk_trace(self, node, val, op=None, children=None, short_circuited=False, error=None):
        if not self.deep_trace: return None
        trace = {
            "NodeType": self._node_type(node),
            "Value": None if short_circuited else self._serialize_value(val),
            "Type": "Null" if short_circuited else self._value_type(val),
            "Children": children or [],
            "ShortCircuited": short_circuited,
        }
        if op is not None:
            trace["Operator"] = op
        if error:
            trace["ErrorCode"] = error.code
            trace["ErrorMessage"] = error.message if hasattr(error, 'message') else str(error)
        return trace

    def _phantom_trace(self, node):
        if not self.deep_trace: return None
        return {
            "NodeType": self._node_type(node),
            "Value": None,
            "Type": "Null",
            "Children": [],
            "ShortCircuited": True,
        }

    # ─── End V11.2 Trace Helpers ──────────────────────────────

    def eval_rule(self, node: RuleNode):
        self.step_count = 0
        self.trace = []
        self._error_trace = None
        try:
            condition_result, root_trace = self.eval_node(node.when_expr)
        except EvaluatorError:
            if self.deep_trace and self._error_trace is not None:
                self.trace = [self._error_trace]
            raise
        except Exception as e:
            raise EvaluatorError("RF4001", f"Unexpected runtime error: {e}")

        if self.deep_trace:
            self.trace = [root_trace]

        actions = node.then_actions if condition_result else (node.else_actions if node.else_actions else [ActionNode("NO_ACTION")])
        resolved_actions = []
        for a in actions:
            if isinstance(a, SetActionNode):
                val, _ = self.eval_node(a.value_node)
                resolved_actions.append(ActionNode("SET", a.value, val))
            elif isinstance(a, EmitActionNode):
                payload = None
                if a.payload_node:
                    payload, _ = self.eval_node(a.payload_node)
                resolved_actions.append(ActionNode("EMIT", a.value, payload))
            else:
                resolved_actions.append(a)
        actions = resolved_actions
        return Decision(node.name, 1, node.lang_version, condition_result, actions, self.trace)

    def _get_date(self, val):
        if isinstance(val, date): return val
        if isinstance(val, str):
            try:
                from datetime import date as d
                parts = val.split("-")
                return d(int(parts[0]), int(parts[1]), int(parts[2]))
            except: raise EvaluatorError("RF4002", "Invalid date format in context")
        raise EvaluatorError("RF4002", "Value is not a date")

    def check_null(self, val, op):
        if val is None: raise EvaluatorError("RF4002", f"Runtime Type Error: Cannot perform '{op}' on NULL. Use IS NULL / IS NOT NULL.")

    def eval_node(self, node):
        self.step_count += 1
        if self.step_count > MAX_EXECUTION_STEPS:
            raise EvaluatorError("RF5003", f"Security Limit: Execution exceeded {MAX_EXECUTION_STEPS} steps")

        try:
            return self._eval_node_impl(node)
        except EvaluatorError as e:
            if self.deep_trace and self._error_trace is None:
                op = getattr(node, 'op', None)
                self._error_trace = self._mk_trace(node, None, op=op, error=e)
            raise

    def _eval_node_impl(self, node):
        if isinstance(node, DateLiteralNode):
            val = node.value
            return val, self._mk_trace(node, val)

        if isinstance(node, LiteralNode):
            if node.type == "IDENTIFIER" and node.value == "it" and "it" in self.context:
                val = self.context["it"]
                return val, self._mk_trace(node, val)
            val = None
            if node.type == "BOOLEAN": val = node.value == "true"
            elif node.type == "INTEGER": val = int(node.value)
            elif node.type == "DECIMAL": val = Decimal(node.value)
            elif node.type == "DATE":
                y, m, d = map(int, node.value.split('-'))
                val = date(y, m, d)
            else: val = node.value
            return val, self._mk_trace(node, val)

        elif isinstance(node, PropertyAccessNode):
            obj = self.context.get(node.obj)
            val = normalize_value(obj.get(node.prop)) if obj else None
            return val, self._mk_trace(node, val)

        elif isinstance(node, IdentifierNode):
            val = normalize_value(self.context.get(node.name))
            return val, self._mk_trace(node, val)

        elif isinstance(node, FilterMapNode):
            arr_val, arr_trace = self.eval_node(node.array_node)
            if not isinstance(arr_val, list):
                raise EvaluatorError("RF4002", "Cannot iterate non-array")
            result = []
            child_traces = [arr_trace]
            for item in arr_val:
                self.context["it"] = item
                res, sub_trace = self.eval_node(node.expr_node)
                child_traces.append(sub_trace)
                if node.is_map:
                    result.append(res)
                else:
                    if res: result.append(item)
            op = "MAP" if node.is_map else "FILTER"
            return result, self._mk_trace(node, result, op=op, children=child_traces)

        elif isinstance(node, AnyAllNode):
            arr_val, arr_trace = self.eval_node(node.array_node)
            if not isinstance(arr_val, list):
                raise EvaluatorError("RF4002", "Cannot iterate non-array")
            child_traces = [arr_trace]
            final_result = node.is_all
            for idx, item in enumerate(arr_val):
                self.context["it"] = item
                res, sub_trace = self.eval_node(node.where_node)
                child_traces.append(sub_trace)
                if node.is_all:
                    if not res:
                        final_result = False
                        for _ in arr_val[idx+1:]:
                            child_traces.append(self._phantom_trace(node.where_node))
                        break
                else:
                    if res:
                        final_result = True
                        for _ in arr_val[idx+1:]:
                            child_traces.append(self._phantom_trace(node.where_node))
                        break
            op = "ALL" if node.is_all else "ANY"
            return final_result, self._mk_trace(node, final_result, op=op, children=child_traces)

        elif isinstance(node, NullCheckNode):
            val, left_trace = self.eval_node(node.left)
            result = val is not None if node.is_not else val is None
            op_str = "IS NOT NULL" if node.is_not else "IS NULL"
            return result, self._mk_trace(node, result, op=op_str, children=[left_trace])

        elif isinstance(node, UnaryOpNode):
            val, operand_trace = self.eval_node(node.operand)
            if node.op == "NOT":
                self.check_null(val, "NOT")
                result = not val
                return result, self._mk_trace(node, result, op="NOT", children=[operand_trace])

        elif isinstance(node, BinaryOpNode):
            op = node.op
            if op == "AND":
                left_val, left_trace = self.eval_node(node.left)
                if not left_val:
                    right_trace = self._phantom_trace(node.right)
                    return False, self._mk_trace(node, False, op="AND", children=[left_trace, right_trace])
                right_val, right_trace = self.eval_node(node.right)
                result = bool(right_val)
                return result, self._mk_trace(node, result, op="AND", children=[left_trace, right_trace])

            elif op == "OR":
                left_val, left_trace = self.eval_node(node.left)
                if left_val:
                    right_trace = self._phantom_trace(node.right)
                    return True, self._mk_trace(node, True, op="OR", children=[left_trace, right_trace])
                right_val, right_trace = self.eval_node(node.right)
                result = True if right_val else False
                return result, self._mk_trace(node, result, op="OR", children=[left_trace, right_trace])

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
            return res, self._mk_trace(node, res, op=op, children=[left_trace, right_trace])

        elif isinstance(node, FunctionCallNode):
            arg_vals = []
            arg_traces = []
            for a in node.args:
                v, t = self.eval_node(a)
                arg_vals.append(v)
                arg_traces.append(t)
            try:
                if node.name.lower() == "contains": self.check_null(arg_vals[0], "contains"); res = arg_vals[1] in arg_vals[0]
                elif node.name.lower() == "length": self.check_null(arg_vals[0], "length"); res = len(arg_vals[0])
                elif node.name.lower() == "starts_with": self.check_null(arg_vals[0], "starts_with"); res = arg_vals[0].startswith(arg_vals[1])
                elif node.name.lower() == "ends_with": self.check_null(arg_vals[0], "ends_with"); res = arg_vals[0].endswith(arg_vals[1])
                elif node.name.lower() == "abs": self.check_null(arg_vals[0], "abs"); res = abs(arg_vals[0])
                elif node.name.lower() == "date_add": self.check_null(arg_vals[0], "date_add"); res = self._get_date(arg_vals[0]) + timedelta(days=arg_vals[1])
                elif node.name.lower() == "date_diff": self.check_null(arg_vals[0], "date_diff"); self.check_null(arg_vals[1], "date_diff"); res = (self._get_date(arg_vals[1]) - self._get_date(arg_vals[0])).days
                elif node.name.lower() == "extract": self.check_null(arg_vals[0], "extract"); d = self._get_date(arg_vals[0]); res = getattr(d, arg_vals[1])
                else: raise EvaluatorError("RF4001", f"Unknown function {node.name}")
            except TypeError as e: raise EvaluatorError("RF4002", f"Runtime Type Error in '{node.name}': {e}")
            return res, self._mk_trace(node, res, op=node.name, children=arg_traces)

        elif isinstance(node, ArrayLiteralNode):
            arr = []
            child_traces = []
            for el in node.elements:
                v, t = self.eval_node(el)
                arr.append(v)
                child_traces.append(t)
            return arr, self._mk_trace(node, arr, children=child_traces)

        elif isinstance(node, ArrayIndexNode):
            arr_val, arr_trace = self.eval_node(node.array)
            idx_val, idx_trace = self.eval_node(node.index)
            self.check_null(arr_val, "INDEXING")
            self.check_null(idx_val, "INDEX")
            if not isinstance(arr_val, list):
                raise EvaluatorError("RF4002", f"Cannot index non-array type {type(arr_val).__name__}")
            if idx_val < 0 or idx_val >= len(arr_val):
                raise EvaluatorError("RF4002", f"Array index out of bounds: {idx_val} (length: {len(arr_val)})")
            result = arr_val[idx_val]
            return result, self._mk_trace(node, result, op="[]", children=[arr_trace, idx_trace])

        raise EvaluatorError("RF4001", f"Unknown AST node {type(node)}")
