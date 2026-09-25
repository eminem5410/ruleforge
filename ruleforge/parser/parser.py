from ..lexer import TokenType
from .ast_nodes import RuleNode, ActionNode, BinaryOpNode, NullCheckNode, LiteralNode, PropertyAccessNode, FunctionCallNode
from .errors import ParserError

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.current_token = self.tokens[self.pos]

    def advance(self):
        self.pos += 1
        if self.pos < len(self.tokens):
            self.current_token = self.tokens[self.pos]

    def expect(self, token_type):
        if self.current_token.type == token_type:
            self.advance()
        else:
            t = self.current_token
            raise ParserError("RF2002", f"Expected {token_type} but got {t.type} ('{t.value}')", t.line, t.column)

    def parse(self):
        rules = []
        while self.current_token.type != TokenType.EOF:
            rules.append(self.parse_rule())
        return rules

    def parse_rule(self):
        self.expect(TokenType.RULE)
        rule_name = self.current_token.value
        self.expect(TokenType.IDENTIFIER)
        
        self.expect(TokenType.LANGUAGE)
        lang_version = int(self.current_token.value)
        self.expect(TokenType.INTEGER)
        
        self.expect(TokenType.WHEN)
        when_expr = self.expression()
        
        self.expect(TokenType.THEN)
        then_actions = self.action_list()
        
        else_actions = []
        if self.current_token.type == TokenType.ELSE:
            self.advance()
            else_actions = self.action_list()
            
        self.expect(TokenType.END)
        return RuleNode(rule_name, lang_version, when_expr, then_actions, else_actions)

    def action_list(self):
        actions = []
        actions.append(self.parse_action())
        while self.current_token.type in [TokenType.ALLOW, TokenType.DENY, TokenType.ALERT, TokenType.APPLY, TokenType.NO_ACTION]:
            actions.append(self.parse_action())
            
        # RF2005 Invalid Action (NO_ACTION must be alone)
        if TokenType.NO_ACTION in [a.action_type for a in actions] and len(actions) > 1:
            t = self.current_token
            raise ParserError("RF2005", "NO_ACTION must be the only action in its block", t.line, t.column)
            
        return actions

    def parse_action(self):
        token = self.current_token
        if token.type in [TokenType.ALLOW, TokenType.NO_ACTION]:
            self.advance()
            return ActionNode(token.value)
        elif token.type in [TokenType.DENY, TokenType.ALERT, TokenType.APPLY]:
            self.advance()
            val_token = self.current_token
            self.expect(TokenType.STRING)
            return ActionNode(token.value, val_token.value)
        raise ParserError("RF2005", f"Expected action but got {token.type}", token.line, token.column)

    # Precedence: OR -> AND -> NOT -> Comparison -> Add/Sub -> Mul/Div -> Primary
    def expression(self):
        return self.logical_or()

    def logical_or(self):
        node = self.logical_and()
        while self.current_token.type == TokenType.OR:
            op = self.current_token.value; self.advance()
            node = BinaryOpNode(node, op, self.logical_and())
        return node

    def logical_and(self):
        node = self.logical_not()
        while self.current_token.type == TokenType.AND:
            op = self.current_token.value; self.advance()
            node = BinaryOpNode(node, op, self.logical_not())
        return node

    def logical_not(self):
        if self.current_token.type == TokenType.NOT:
            self.advance()
            return BinaryOpNode(None, "NOT", self.logical_not())
        return self.comparison()

    def comparison(self):
        node = self.arithmetic()
        
        if self.current_token.type == TokenType.IS:
            self.advance()
            is_not = False
            if self.current_token.type == TokenType.NOT:
                self.advance()
                is_not = True
            self.expect(TokenType.NULL)
            return NullCheckNode(node, is_not)
            
        while self.current_token.type in [TokenType.EQ, TokenType.NEQ, TokenType.GT, TokenType.LT, TokenType.GTE, TokenType.LTE]:
            op = self.current_token.value; self.advance()
            node = BinaryOpNode(node, op, self.arithmetic())
        return node

    def arithmetic(self):
        node = self.term()
        while self.current_token.type in [TokenType.PLUS, TokenType.MINUS]:
            op = self.current_token.value; self.advance()
            node = BinaryOpNode(node, op, self.term())
        return node

    def term(self):
        node = self.factor()
        while self.current_token.type in [TokenType.MULTIPLY, TokenType.DIVIDE]:
            op = self.current_token.value; self.advance()
            node = BinaryOpNode(node, op, self.factor())
        return node

    def factor(self):
        token = self.current_token
        
        if token.type == TokenType.LPAREN:
            self.advance()
            expr = self.expression()
            self.expect(TokenType.RPAREN)
            return expr
            
        elif token.type in [TokenType.INTEGER, TokenType.DECIMAL, TokenType.STRING, TokenType.BOOLEAN, TokenType.DATE]:
            self.advance()
            return LiteralNode(token.value, token.type)
            
        elif token.type == TokenType.IDENTIFIER:
            name = token.value
            self.advance()
            
            if self.current_token.type == TokenType.LPAREN:
                self.advance()
                args = []
                if self.current_token.type != TokenType.RPAREN:
                    args.append(self.expression())
                    while self.current_token.type == TokenType.COMMA:
                        self.advance()
                        args.append(self.expression())
                self.expect(TokenType.RPAREN)
                return FunctionCallNode(name, args)
                
            elif self.current_token.type == TokenType.DOT:
                self.advance()
                prop_token = self.current_token
                self.expect(TokenType.IDENTIFIER)
                return PropertyAccessNode(name, prop_token.value)
                
            return LiteralNode(token.value, token.type) 
            
        elif token.type == TokenType.EOF:
            raise ParserError("RF2003", "Unexpected EOF, expected expression", token.line, token.column)
            
        raise ParserError("RF2004", f"Invalid expression, unexpected token {token.type}", token.line, token.column)
