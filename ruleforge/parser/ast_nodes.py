class RuleNode:
    def __init__(self, name, lang_version, when_expr, then_actions, else_actions):
        self.name = name; self.lang_version = lang_version
        self.when_expr = when_expr; self.then_actions = then_actions; self.else_actions = else_actions
    def __repr__(self): return f"RuleNode(name='{self.name}', lang={self.lang_version})"

class ActionNode:
    def __init__(self, action_type, value=None, payload=None):
        self.action_type = action_type
        self.value = value
        self.payload = payload
        self.action_type = action_type; self.value = value
    def __repr__(self): return f"Action({self.action_type}, val='{self.value}')"
    def to_dict(self):
        return {"type": self.action_type, "value": self.value if self.value != 'None' else None}

class BinaryOpNode:
    def __init__(self, left, op, right):
        self.left = left; self.op = op; self.right = right
    def __repr__(self): return f"BinOp({self.left} {self.op} {self.right})"

class UnaryOpNode:
    def __init__(self, op, operand):
        self.op = op; self.operand = operand
    def __repr__(self): return f"UnaryOp({self.op} {self.operand})"

class NullCheckNode:
    def __init__(self, left, is_not):
        self.left = left; self.is_not = is_not
    def __repr__(self): return f"NullCheck({self.left} IS {'NOT ' if self.is_not else ''}NULL)"

class LiteralNode:
    def __init__(self, value, type):
        self.value = value; self.type = type
    def __repr__(self): return f"Lit({self.value})"

class IdentifierNode:
    def __init__(self, name):
        self.name = name
    def __repr__(self): return f"Ident({self.name})"

class PropertyAccessNode:
    def __init__(self, obj, prop):
        self.obj = obj; self.prop = prop
    def __repr__(self): return f"Prop({self.obj}.{self.prop})"

class FunctionCallNode:
    def __init__(self, name, args):
        self.name = name; self.args = args
    def __repr__(self): return f"FuncCall({self.name}, args={self.args})"

class ArrayLiteralNode:
    def __init__(self, elements):
        self.elements = elements
    def __repr__(self): return f"ArrayLit({self.elements})"

class ArrayIndexNode:
    def __init__(self, array_expr, index):
        self.array = array_expr; self.index = index
    def __repr__(self): return f"ArrayIndex({self.array}[{self.index}])"

class DateLiteralNode:
    def __init__(self, value: str):
        from datetime import date
        parts = value.split("-")
        self.value = date(int(parts[0]), int(parts[1]), int(parts[2]))
    def __repr__(self): return f"DateLiteral({self.value})"

class EmitActionNode(ActionNode):
    def __init__(self, intent_name, payload_node=None):
        super().__init__("EMIT", intent_name)
        self.payload_node = payload_node
    def __repr__(self): return f"EmitAction({self.value}, payload={self.payload_node})"

class SetActionNode(ActionNode):
    def __init__(self, obj_name, prop_name, value_node):
        super().__init__("SET", f"{obj_name}.{prop_name}")
        self.obj_name = obj_name
        self.prop_name = prop_name
        self.value_node = value_node

class AnyAllNode:
    def __init__(self, is_all, array_node, where_node):
        self.is_all = is_all
        self.array_node = array_node
        self.where_node = where_node
    def __repr__(self): return f"AnyAll({'ALL' if self.is_all else 'ANY'} {self.array_node} WHERE {self.where_node})"

class FilterMapNode:
    def __init__(self, is_map, array_node, expr_node):
        self.is_map = is_map
        self.array_node = array_node
        self.expr_node = expr_node
    def __repr__(self): return f"FilterMap({'MAP' if self.is_map else 'FILTER'} {self.array_node} {'USING' if self.is_map else 'WHERE'} {self.expr_node})"
