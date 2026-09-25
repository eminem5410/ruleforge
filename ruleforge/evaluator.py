from .ast_nodes import *

class Decision:
    def __init__(self, rule_name, matched, action_type, action_value=None, trace=None):
        self.rule_name=rule_name; self.matched=matched; self.action_type=action_type; self.action_value=action_value; self.trace=trace or []
    def __repr__(self): return f"Decision(rule='{self.rule_name}', matched={self.matched}, action={self.action_type})"

class Evaluator:
    def __init__(self, context, explain_mode=False):
        self.context=context; self.explain_mode=explain_mode; self.trace=[]
    def eval_rule(self, rule_node):
        self.trace=[]; condition_result=self.eval_expression(rule_node.when_expr)
        if self.explain_mode: self.trace.append(f"CONDICIÓN FINAL EVALUADA COMO: {condition_result}")
        if condition_result: action=rule_node.then_action; matched=True
        else:
            if rule_node.else_action: action=rule_node.else_action; matched=False
            else: action=ActionNode("NO_ACTION"); matched=False
        return Decision(rule_node.name,matched,action.action_type,action.value,self.trace)
    def eval_expression(self, node):
        if isinstance(node, LiteralNode):
            if node.type=="BOOLEAN": return node.value=="true"
            return node.value
        elif isinstance(node, PropertyAccessNode):
            obj=self.context.get(node.obj)
            return None if obj is None else obj.get(node.prop)
        elif isinstance(node, NullCheckNode):
            val=self.eval_expression(node.left)
            result=val is not None if node.is_not else val is None
            if self.explain_mode: self.trace.append(f"Evaluando: {val} IS {'NOT ' if node.is_not else ''}NULL -> {result}")
            return result
        elif isinstance(node, BinaryOpNode):
            left_val=self.eval_expression(node.left); right_val=self.eval_expression(node.right); op=node.op
            if op=="AND": result=left_val and right_val
            elif op=="OR": result=left_val or right_val
            elif op=="==": result=left_val==right_val
            elif op=="!=": result=left_val!=right_val
            elif op==">": result=left_val>right_val
            elif op=="<": result=left_val<right_val
            elif op==">=": result=left_val>=right_val
            elif op=="<=": result=left_val<=right_val
            else: raise Exception(f"RF4001 Runtime Error: Unsupported operator {op}")
            if self.explain_mode: self.trace.append(f"Evaluando: {left_val} {op} {right_val} -> {result}")
            return result
        elif isinstance(node, FunctionCallNode):
            args=[self.eval_expression(arg) for arg in node.args]
            if node.name=="contains": result=args[1] in args[0]
            elif node.name=="length": result=len(args[0])
            elif node.name=="abs": result=abs(args[0])
            else: raise Exception(f"RF4001 Runtime Error: Unknown function {node.name}")
            if self.explain_mode: self.trace.append(f"Evaluando función: {node.name}({args}) -> {result}")
            return result
