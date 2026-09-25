class RuleNode:
    def __init__(self, name, lang_version, when_expr, then_actions, else_actions):
        self.name = name; self.lang_version = lang_version
        self.when_expr = when_expr; self.then_actions = then_actions; self.else_actions = else_actions
    def __repr__(self): return f"RuleNode(name='{self.name}', lang={self.lang_version})"

class ActionNode:
    def __init__(self, action_type, value=None):
        self.action_type = action_type
        self.value = value
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
