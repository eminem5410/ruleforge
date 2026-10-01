import copy
import hashlib
from collections import OrderedDict
from datetime import date, datetime
from decimal import Decimal
from .lexer import Lexer
from .parser import Parser, ParserError
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

class RuleTraceEntry:
    def __init__(self, rule_name, rule_index, matched, applied_patches, actions, evaluation_trace=None):
        self.rule_name = rule_name
        self.rule_index = rule_index
        self.matched = matched
        self.applied_patches = applied_patches
        self.actions = actions
        self.evaluation_trace = evaluation_trace

class PipelineResult:
    def __init__(self, decisions, applied_patches, final_context, trace):
        self.decisions = decisions
        self.applied_patches = applied_patches
        self.final_context = final_context
        self.trace = trace

class RuleEngine:
    def __init__(self, schema, use_compiler=False, max_cache_size=100):
        self.schema = schema
        self.use_compiler = use_compiler
        self._max_cache_size = max_cache_size
        self._ast_cache = OrderedDict()
        self._cache_hits = 0
        self._cache_misses = 0

    def _cache_key(self, source_code):
        schema_repr = repr(sorted(self.schema.items()))
        return hashlib.sha256(f"{source_code}::{schema_repr}".encode()).hexdigest()

    def _get_or_parse(self, source_code):
        if self._max_cache_size <= 0:
            self._cache_misses += 1
            return self._parse_and_compile(source_code)

        key = self._cache_key(source_code)

        if key in self._ast_cache:
            self._cache_hits += 1
            self._ast_cache.move_to_end(key)
            return self._ast_cache[key]

        self._cache_misses += 1
        result = self._parse_and_compile(source_code)

        self._ast_cache[key] = result
        if len(self._ast_cache) > self._max_cache_size:
            self._ast_cache.popitem(last=False)

        return result

    def _parse_and_compile(self, source_code):
        tokens = Lexer(source_code).tokenize()
        ast = Parser(tokens).parse()

        if not ast:
            raise ParserError("RF2003", "No rules found in source", 1, 1)

        SemanticAnalyzer(self.schema).analyze(ast)
        compiler = RuleForgeCompiler(ast) if self.use_compiler else None
        return (ast, compiler)

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
                                    normalized_date = date(int(parts[0]), int(parts[1]), int(parts[2]))
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

    def evaluate(self, source_code, context, explain=False, trace=False):
        ast, cached_compiler = self._get_or_parse(source_code)

        self._validate_context(context)
        working_context = copy.deepcopy(context)
        
        evaluator = Evaluator(working_context, deep_trace=(explain or trace))
        compiler = cached_compiler if (cached_compiler and not explain) else None
        
        decisions = []
        applied_patches = []
        trace_entries = [] if trace else None
        
        for i, rule in enumerate(ast):
            if not compiler or not compiler.compiled_conditions.get(id(rule)):
                decision = evaluator.eval_rule(rule)
            else:
                decision = compiler.execute_single(rule, working_context)
            decisions.append(decision)
            
            rule_applied_paths = []
            rule_actions = [a.action_type for a in decision.actions]
            
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
                        rule_applied_paths.append(path)
                        patch_index += 1
            
            if trace:
                trace_entries.append(RuleTraceEntry(
                    rule_name=rule.name,
                    rule_index=i,
                    matched=decision.matched,
                    applied_patches=rule_applied_paths,
                    actions=rule_actions,
                    evaluation_trace=decision.trace[0] if decision.trace else None
                ))
                    
        return PipelineResult(decisions, applied_patches, working_context, trace_entries)
