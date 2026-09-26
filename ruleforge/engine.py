from datetime import date
from decimal import Decimal
from .lexer import Lexer, LexerError
from .parser import Parser, ParserError
from .semantic import SemanticAnalyzer, SemanticError
from .evaluator import Evaluator, EvaluatorError

class RuleForgeEngine:
    def __init__(self, context_schema):
        self.schema = context_schema

    def _validate_and_coerce_context(self, context_data):
        if not isinstance(context_data, dict):
            raise EvaluatorError("RF4003", f"Invalid Runtime Context: Expected a JSON object, but got {type(context_data).__name__}")

        for obj_name, props in self.schema.items():
            obj_val = context_data.get(obj_name)
            
            if obj_val is None: 
                continue
                
            if not isinstance(obj_val, dict):
                raise EvaluatorError("RF4003", f"Invalid Runtime Context: Expected object for '{obj_name}' but got {type(obj_val).__name__}")
                
            for prop_name, expected_type in props.items():
                if prop_name in obj_val:
                    val = obj_val[prop_name]
                    if val is None: 
                        continue
                        
                    actual_type = type(val).__name__
                    
                    # --- INICIO VALIDACIÓN DE ARRAYS ---
                    if expected_type.startswith("Array<"):
                        if not isinstance(val, list):
                            raise EvaluatorError("RF4003", f"Invalid Runtime Context: Property '{obj_name}.{prop_name}' expected Array but got {actual_type}")
                        inner_type = expected_type[6:-1]
                        for i, item in enumerate(val):
                            item_type = type(item).__name__
                            if inner_type == "Integer":
                                if not (isinstance(item, int) and not isinstance(item, bool)):
                                    raise EvaluatorError("RF4003", f"Invalid Runtime Context: Element {i} of '{obj_name}.{prop_name}' expected Integer but got {item_type}")
                            elif inner_type == "Decimal":
                                if not (isinstance(item, (int, float)) and not isinstance(item, bool)):
                                    raise EvaluatorError("RF4003", f"Invalid Runtime Context: Element {i} of '{obj_name}.{prop_name}' expected Decimal but got {item_type}")
                                obj_val[prop_name][i] = Decimal(str(item))
                            elif inner_type == "String":
                                if not isinstance(item, str):
                                    raise EvaluatorError("RF4003", f"Invalid Runtime Context: Element {i} of '{obj_name}.{prop_name}' expected String but got {item_type}")
                            elif inner_type == "Boolean":
                                if not isinstance(item, bool):
                                    raise EvaluatorError("RF4003", f"Invalid Runtime Context: Element {i} of '{obj_name}.{prop_name}' expected Boolean but got {item_type}")
                            elif inner_type == "Date":
                                if not isinstance(item, str):
                                    raise EvaluatorError("RF4003", f"Invalid Runtime Context: Element {i} of '{obj_name}.{prop_name}' expected Date but got {item_type}")
                                try:
                                    y, m, d = map(int, item.split('-'))
                                    obj_val[prop_name][i] = date(y, m, d)
                                except Exception:
                                    raise EvaluatorError("RF4003", f"Invalid Runtime Context: Element {i} of '{obj_name}.{prop_name}' has invalid Date format: {item}")
                                    
                    # --- FIN VALIDACIÓN DE ARRAYS ---
                    
                    elif expected_type == "Integer":
                        if not (isinstance(val, int) and not isinstance(val, bool)):
                            raise EvaluatorError("RF4003", f"Invalid Runtime Context: Property '{obj_name}.{prop_name}' expected Integer but got {actual_type}")
                    elif expected_type == "Decimal":
                        if not (isinstance(val, (int, float)) and not isinstance(val, bool)):
                            raise EvaluatorError("RF4003", f"Invalid Runtime Context: Property '{obj_name}.{prop_name}' expected Decimal but got {actual_type}")
                        if isinstance(val, (int, float)):
                            obj_val[prop_name] = Decimal(str(val))
                    elif expected_type == "String":
                        if not isinstance(val, str):
                            raise EvaluatorError("RF4003", f"Invalid Runtime Context: Property '{obj_name}.{prop_name}' expected String but got {actual_type}")
                    elif expected_type == "Boolean":
                        if not isinstance(val, bool):
                            raise EvaluatorError("RF4003", f"Invalid Runtime Context: Property '{obj_name}.{prop_name}' expected Boolean but got {actual_type}")
                    elif expected_type == "Date":
                        if not isinstance(val, str):
                            raise EvaluatorError("RF4003", f"Invalid Runtime Context: Property '{obj_name}.{prop_name}' expected Date but got {actual_type}")
                        try:
                            y, m, d = map(int, val.split('-'))
                            obj_val[prop_name] = date(y, m, d)
                        except Exception:
                            raise EvaluatorError("RF4003", f"Invalid Runtime Context: Property '{obj_name}.{prop_name}' has invalid Date format: {val}")

    def evaluate(self, rule_source, context_data, explain=False):
        # 1. Parse and Static Semantic Analysis
        lexer = Lexer(rule_source)
        tokens = lexer.tokenize()
        
        parser = Parser(tokens)
        ast = parser.parse()
        
        analyzer = SemanticAnalyzer(self.schema)
        analyzer.analyze(ast)
        
        # 2. Runtime Context Validation & Coercion
        self._validate_and_coerce_context(context_data)
        
        # 3. Evaluation
        evaluator = Evaluator(context_data, explain_mode=explain)
        decisions = evaluator.eval_rules(ast)
        
        return decisions
