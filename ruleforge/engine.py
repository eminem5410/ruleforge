import copy
from datetime import date, datetime
from decimal import Decimal
from .lexer import Lexer
from .parser import Parser
from .semantic import SemanticAnalyzer
from .evaluator import Evaluator, EvaluatorError
from .compiler import RuleForgeCompiler
from .parser.ast_nodes import RuleNode, ActionNode

class AppliedPatch:
    def __init__(self, rule_name, rule_index, patch_index, path, old_value, new_value):
        self.rule_name = rule_name
        self.rule_index = rule_index
        self.patch_index = patch_index
        self.path = path
        self.old_value = old_value
        self.new_value = new_value

class RuleEngine:
    def __init__(self, schema, use_compiler=False):
        self.schema = schema
        self.use_compiler = use_compiler

    def _validate_context(self, context):
        if not isinstance(context, dict):
            raise EvaluatorError("RF4003", "Expected a JSON object, but got list or other type.")
        for obj_name, props in self.schema.items():
            if obj_name in context:
                if context[obj_name] is None: continue
                if not isinstance(context[obj_name], dict):
                    raise EvaluatorError("RF4003", f"Expected object for '{obj_name}' but got {type(context[obj_name]).__name__}.")
                for prop_name, prop_type in props.items():
                    if prop_name in context[obj_name] and context[obj_name][prop_name] is not None:
                        val = context[obj_name][prop_name]
                        try:
                            if prop_type == "Integer" and (not isinstance(val, int) or isinstance(val, bool)): raise ValueError()
                            if prop_type == "Decimal" and not isinstance(val, (int, float, Decimal)): raise ValueError()
                            if prop_type == "String" and not isinstance(val, str): raise ValueError()
                            if prop_type == "Boolean" and not isinstance(val, bool): raise ValueError()
                            if prop_type == "Date":
                                if isinstance(val, str):
                                    parts = val.split("-")
                                    normalized_date = date(
                                        int(parts[0]),
                                        int(parts[1]),
                                        int(parts[2])
                                    )
                                    context[obj_name][prop_name] = normalized_date
                                elif isinstance(val, datetime):
                                    context[obj_name][prop_name] = val.date()
                                elif not isinstance(val, date):
                                    raise ValueError()
                            if prop_type.startswith("Array<"):
                                if not isinstance(val, list):
                                    raise EvaluatorError("RF4003", f"expected Array but got {type(val).__name__}")
                                inner_type = prop_type[6:-1]
                                for item in val:
                                    if inner_type == "Integer" and (not isinstance(item, int) or isinstance(item, bool)):
                                        raise EvaluatorError("RF4003", f"expected {inner_type} but got {type(item).__name__}")
                                    if inner_type == "String" and not isinstance(item, str):
                                        raise EvaluatorError("RF4003", f"expected {inner_type} but got {type(item).__name__}")
                        except (ValueError, TypeError):
                            raise EvaluatorError("RF4003", f"expected {prop_type} but got {type(val).__name__}")

    def evaluate(self, source_code, context, explain=False):
        tokens = Lexer(source_code).tokenize()
        ast = Parser(tokens).parse()
        SemanticAnalyzer(self.schema).analyze(ast)
        
        self._validate_context(context)
        working_context = copy.deepcopy(context)
        
        evaluator = Evaluator(working_context, explain_mode=explain)
        compiler = RuleForgeCompiler(ast) if (self.use_compiler and not explain) else None
        
        decisions = []
        applied_patches = []
        
        for i, rule in enumerate(ast):
            if compiler and compiler.compiled_conditions.get(id(rule)):
                decision = compiler.execute(working_context)[i]
            else:
                decision = evaluator.eval_rule(rule)
                
            decisions.append(decision)
            
            if decision.matched:
                patch_index = 0
                for action in decision.actions:
                    if action.action_type == "SET":
                        path = action.value
                        new_value = action.payload
                        obj_name, prop_name = path.split(".")
                        old_value = working_context.get(obj_name, {}).get(prop_name)
                        
                        if obj_name not in working_context or not isinstance(working_context[obj_name], dict):
                            working_context[obj_name] = {}
                            
                        working_context[obj_name][prop_name] = new_value
                        
                        applied_patches.append(AppliedPatch(
                            rule_name=rule.name, rule_index=i, patch_index=patch_index,
                            path=path, old_value=old_value, new_value=new_value
                        ))
                        patch_index += 1
                        
        return decisions
