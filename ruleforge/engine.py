from .lexer import Lexer
from .parser import Parser
from .semantic import SemanticAnalyzer
from .evaluator import Evaluator
from .errors import LexerError, ParserError, SemanticError, EvaluatorError

class RuleForgeEngine:
    def __init__(self, context_schema):
        self.schema = context_schema

    def evaluate(self, rule_source, context_data, explain=False):
        # Pipeline completo de RuleForge
        lexer = Lexer(rule_source)
        tokens = lexer.tokenize()
        
        parser = Parser(tokens)
        ast = parser.parse()
        
        analyzer = SemanticAnalyzer(self.schema)
        analyzer.analyze(ast)
        
        evaluator = Evaluator(context_data, explain_mode=explain)
        decisions = evaluator.eval_rules(ast)
        
        return decisions
