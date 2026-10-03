from decimal import Decimal, InvalidOperation
from datetime import date, timedelta
import operator as _op
from ..parser.ast_nodes import (RuleNode, ActionNode, BinaryOpNode, UnaryOpNode,
    NullCheckNode, LiteralNode, IdentifierNode, PropertyAccessNode, MatchNode,
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
        self._it_stack = []
        self._bin_ops = {'==': _op.eq, '!=': _op.ne, '>': _op.gt, '<': _op.lt, '>=': _op.ge, '<=': _op.le, '+': _op.add, '-': _op.sub, '*': _op.mul, '/': _op.truediv}
        self._dispatchers = {DateLiteralNode: self._eval_date_literal, LiteralNode: self._eval_literal, PropertyAccessNode: self._eval_property_access, IdentifierNode: self._eval_identifier, FilterMapNode: self._eval_filter_map, AnyAllNode: self._eval_any_all, NullCheckNode: self._eval_null_check, UnaryOpNode: self._eval_unary_op, BinaryOpNode: self._eval_binary_op, FunctionCallNode: self._eval_function_call, ArrayLiteralNode: self._eval_array_literal, ArrayIndexNode: self._eval_array_index}
        self._error_trace = None
        if not self.deep_trace:
            self._mk_trace = lambda *args, **kwargs: None
            self._phantom_trace = lambda *args, **kwargs: None

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
        if node.match_node:
            raise EvaluatorError("RF4001", "MATCH Evaluator not implemented in V12.0-rc.1")
        self.step_count = 0
        self._it_stack = []
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
        try:
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
        except EvaluatorError:
            raise
        except Exception as e:
            raise EvaluatorError("RF4001", f"Unexpected runtime error in action: {e}")
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
        handler = _DISPATCHERS.get(type(node))
        if handler is None:
            raise EvaluatorError("RF5004", f"V11.2: Unmapped AST node type {type(node).__name__}")
        return handler(self, node)

    def _eval_date_literal(self, node):
        val = node.value
        return val, self._mk_trace(node, val)

    def _eval_literal(self, node):
        if node.type == "IDENTIFIER" and node.value == "it" and self._it_stack:
            val = self._it_stack[-1]
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

    def _eval_property_access(self, node):
        if node.obj == "it" and self._it_stack:
            obj = self._it_stack[-1]
        else:
            obj = self.context.get(node.obj)
        val = normalize_value(obj.get(node.prop)) if obj else None
        return val, self._mk_trace(node, val)

    def _eval_identifier(self, node):
        if node.name == "it" and self._it_stack:
            val = self._it_stack[-1]
        else:
            val = self.context.get(node.name)
        return normalize_value(val), self._mk_trace(node, val)

    def _eval_filter_map(self, node):
        arr_val, arr_trace = self.eval_node(node.array_node)
        if not isinstance(arr_val, list):
            raise EvaluatorError("RF4002", "Cannot iterate non-array")
        result = []
        child_traces = [arr_trace]
        for item in arr_val:
            self._it_stack.append(item)
            try:
                res, sub_trace = self.eval_node(node.expr_node)
            finally:
                self._it_stack.pop()
            child_traces.append(sub_trace)
            if node.is_map:
                result.append(res)
            else:
                if res: result.append(item)
        op = "MAP" if node.is_map else "FILTER"
        return result, self._mk_trace(node, result, op=op, children=child_traces)

    def _eval_any_all(self, node):
        arr_val, arr_trace = self.eval_node(node.array_node)
        if not isinstance(arr_val, list):
            raise EvaluatorError("RF4002", "Cannot iterate non-array")
        child_traces = [arr_trace]
        final_result = node.is_all
        for idx, item in enumerate(arr_val):
            self._it_stack.append(item)
            try:
                res, sub_trace = self.eval_node(node.where_node)
            finally:
                self._it_stack.pop()
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

    def _eval_null_check(self, node):
        val, left_trace = self.eval_node(node.left)
        result = val is not None if node.is_not else val is None
        op_str = "IS NOT NULL" if node.is_not else "IS NULL"
        return result, self._mk_trace(node, result, op=op_str, children=[left_trace])

    def _eval_unary_op(self, node):
        val, operand_trace = self.eval_node(node.operand)
        if node.op == "NOT":
            self.check_null(val, "NOT")
            result = not val
            return result, self._mk_trace(node, result, op="NOT", children=[operand_trace])

    def _eval_binary_op(self, node):
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
        
        if left_val is None or right_val is None:
            raise EvaluatorError("RF4002", f"Runtime Type Error: Cannot perform '{op}' on NULL. Use IS NULL / IS NOT NULL.")
            
        try:
            if op == "/":
                if right_val == 0: raise EvaluatorError("RF4001", "Division by zero")
            res = self._bin_ops[op](left_val, right_val)
        except TypeError as e: raise EvaluatorError("RF4002", f"Runtime Type Error: {e}")
        except InvalidOperation as e: raise EvaluatorError("RF4002", f"Decimal Runtime Error: {e}")
        return res, self._mk_trace(node, res, op=op, children=[left_trace, right_trace])

    def _eval_function_call(self, node):
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

    def _eval_array_literal(self, node):
        arr = []
        child_traces = []
        for el in node.elements:
            v, t = self.eval_node(el)
            arr.append(v)
            child_traces.append(t)
        return arr, self._mk_trace(node, arr, children=child_traces)

    def _eval_array_index(self, node):
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

# V11.8.6: Static dispatcher table (no bound methods created per lookup)
_DISPATCHERS = {
    DateLiteralNode: Evaluator._eval_date_literal,
    LiteralNode: Evaluator._eval_literal,
    PropertyAccessNode: Evaluator._eval_property_access,
    IdentifierNode: Evaluator._eval_identifier,
    FilterMapNode: Evaluator._eval_filter_map,
    AnyAllNode: Evaluator._eval_any_all,
    NullCheckNode: Evaluator._eval_null_check,
    UnaryOpNode: Evaluator._eval_unary_op,
    BinaryOpNode: Evaluator._eval_binary_op,
    FunctionCallNode: Evaluator._eval_function_call,
    ArrayLiteralNode: Evaluator._eval_array_literal,
    ArrayIndexNode: Evaluator._eval_array_index,
}
