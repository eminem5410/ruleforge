from datetime import date
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
                    
                    if expected_type == "Integer":
                        if not (isinstance(val, int) and not isinstance(val, bool)):
                            raise EvaluatorError("RF4003", f"Invalid Runtime Context: Property '{obj_name}.{prop_name}' expected Integer but got {actual_type}")
                    elif expected_type == "Decimal":
                        if not (isinstance(val, (int, float)) and not isinstance(val, bool)):
                            raise EvaluatorError("RF4003", f"Invalid Runtime Context: Property '{obj_name}.{prop_name}' expected Decimal but got {actual_type}")
                    elif expected_type == "String":
                        if not isinstance(val, str):
                            raise EvaluatorError("RF4003", f"Invalid Runtime Context: Property '{obj_name}.{prop_name}' expected String but got {actual_type}")
                    elif expected_type == "Boolean":
                        if not isinstance(val, bool):
                            raise EvaluatorError("RF4003", f"Invalid Runtime Context: Property '{obj_name}.{prop_name}' expected Boolean but got {actual_type}")
                    elif expected_type == "Date":
                        if not isinstance(val, str):
                            raise EvaluatorError("RF4003", f"Invalid Runtime Context: Property '{obj_name}.{prop_name}' expected Date but got {actual_type}")
                        # Coerción segura: Convertir string ISO a date object para el Evaluator
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
