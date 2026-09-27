from ..evaluator import Evaluator


class RuleForgeCompiler:
    """
    V9.0.0-alpha: Passthrough compiler.

    The compiler currently delegates execution to the normative interpreter.
    Future V9 versions will replace this implementation with AST compilation.
    """

    def __init__(self, ast):
        self.ast = ast

    def execute(self, context):
        # V9 Alpha: compiler delegates directly to the interpreter.
        evaluator = Evaluator(context)
        return evaluator.eval_rules(self.ast)
