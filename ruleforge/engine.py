from .lexer import Lexer
from .parser import Parser
from .evaluator import Evaluator
from .semantic_analyzer import SemanticAnalyzer

class RuleForgeEngine:
    def __init__(self, context_schema):
        self.schema = context_schema

    def evaluate(self, rule_source, context_data, explain=False):
        lexer = Lexer(rule_source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast_list = parser.parse()
        
        evaluator = Evaluator(context_data, explain_mode=explain)
        decisions = []
        
        for ast in ast_list:
            analyzer = SemanticAnalyzer(self.schema)
            analyzer.analyze(ast)
            decisions.append(evaluator.eval_rule(ast))
            
        return decisions
