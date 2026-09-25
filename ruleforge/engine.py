from .lexer import Lexer, LexerError
from .parser import Parser, ParserError
from .semantic import SemanticAnalyzer, SemanticError
from .evaluator import Evaluator, EvaluatorError

class RuleForgeEngine:
    def __init__(self, context_schema):
        self.schema = context_schema

    def _validate_context(self, context_data):
        if not isinstance(context_data, dict):
            raise EvaluatorError("RF4003", f"Invalid Runtime Context: Expected a JSON object, but got {type(context_data).__name__}")

        for obj_name, props in self.schema.items():
            obj_val = context_data.get(obj_name)
            
            if obj_val is None: 
                continue # Missing object in context, treated as NULL everywhere
                
            if not isinstance(obj_val, dict):
                raise EvaluatorError("RF4003", f"Invalid Runtime Context: Expected object for '{obj_name}' but got {type(obj_val).__name__}")
                
            for prop_name, expected_type in props.items():
                if prop_name in obj_val:
                    val = obj_val[prop_name]
                    if val is None: 
                        continue # NULL is allowed
                        
                    is_valid = False
                    actual_type = type(val).__name__
                    
                    if expected_type == "Integer":
                        is_valid = isinstance(val, int) and not isinstance(val, bool)
                    elif expected_type == "Decimal":
                        is_valid = isinstance(val, (int, float)) and not isinstance(val, bool)
                    elif expected_type == "String":
                        is_valid = isinstance(val, str)
                    elif expected_type == "Boolean":
                        is_valid = isinstance(val, bool)
                    elif expected_type == "Date":
                        is_valid = isinstance(val, str) # Kept as string until Evaluator parses it to date object
                        
                    if not is_valid:
                        raise EvaluatorError("RF4003", f"Invalid Runtime Context: Property '{obj_name}.{prop_name}' expected {expected_type} but got {actual_type}")

    def evaluate(self, rule_source, context_data, explain=False):
        # 1. Parse and Static Semantic Analysis
        lexer = Lexer(rule_source)
        tokens = lexer.tokenize()
        
        parser = Parser(tokens)
        ast = parser.parse()
        
        analyzer = SemanticAnalyzer(self.schema)
        analyzer.analyze(ast)
        
        # 2. Runtime Context Validation (NEW)
        self._validate_context(context_data)
        
        # 3. Evaluation
        evaluator = Evaluator(context_data, explain_mode=explain)
        decisions = evaluator.eval_rules(ast)
        
        return decisions
