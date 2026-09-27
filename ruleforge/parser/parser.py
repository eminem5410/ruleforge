from ..lexer import TokenType
from .ast_nodes import RuleNode, ActionNode, BinaryOpNode, UnaryOpNode, NullCheckNode, LiteralNode, IdentifierNode, PropertyAccessNode, FunctionCallNode
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
            t = self.current_token
            self.advance()
            return t
        else:
            t = self.current_token
            raise ParserError("RF2002", f"Expected {token_type} but got {t.type} ('{t.value}')", t.line, t.column)

    def parse(self):
        # Soporta múltiples reglas por archivo: { rule }
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
        
        # Validación estricta de NO_ACTION
        if actions[0].action_type == "NO_ACTION":
            if self.current_token.type in [TokenType.ALLOW, TokenType.DENY, TokenType.ALERT, TokenType.APPLY, TokenType.NO_ACTION, TokenType.EMIT, TokenType.SET]:
                t = self.current_token
                raise ParserError("RF2005", "NO_ACTION must be the only action in its block", t.line, t.column)
        else:
            while self.current_token.type in [TokenType.ALLOW, TokenType.DENY, TokenType.ALERT, TokenType.APPLY, TokenType.EMIT, TokenType.SET]:
                actions.append(self.parse_action())
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
        if token.type == TokenType.EMIT:
            self.advance()
            str_token = self.expect(TokenType.STRING)
            intent_name = str_token.value
            payload_node = None
            if self.current_token.type == TokenType.WITH:
                self.advance()
                obj_name = self.current_token.value
                self.expect(TokenType.IDENTIFIER)
                self.expect(TokenType.DOT)
                prop_name = self.current_token.value
                self.expect(TokenType.IDENTIFIER)
                payload_node = PropertyAccessNode(obj_name, prop_name)
            from .ast_nodes import EmitActionNode
            return EmitActionNode(intent_name, payload_node)
        if token.type == TokenType.SET:
            self.advance()
            obj_name = self.current_token.value
            self.expect(TokenType.IDENTIFIER)
            self.expect(TokenType.DOT)
            prop_name = self.current_token.value
            self.expect(TokenType.IDENTIFIER)
            self.expect(TokenType.ASSIGN)
            value_node = self.expression()
            from .ast_nodes import SetActionNode
            return SetActionNode(obj_name, prop_name, value_node)
        raise ParserError("RF2005", f"Expected action but got {token.type}", token.line, token.column)

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
            return UnaryOpNode("NOT", self.logical_not())
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
            
        # Fix: 'if' en lugar de 'while' para evitar a < b < c
        if self.current_token.type in [TokenType.EQ, TokenType.NEQ, TokenType.GT, TokenType.LT, TokenType.GTE, TokenType.LTE]:
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
        if token.type == TokenType.DATE:
            self.advance()
            str_token = self.expect(TokenType.STRING)
            from .ast_nodes import DateLiteralNode
            return DateLiteralNode(str_token.value)
            str_token = self.expect(TokenType.STRING)
            from .ast_nodes import DateLiteralNode
            return DateLiteralNode(str_token.value)

            str_token = self.expect(TokenType.STRING)
            from .ast_nodes import DateLiteralNode
            return DateLiteralNode(str_token.value)
        if token.type == TokenType.LPAREN:
            self.advance()
            expr = self.expression()
            self.expect(TokenType.RPAREN)
            return expr
        elif token.type in [TokenType.INTEGER, TokenType.DECIMAL, TokenType.STRING, TokenType.BOOLEAN]:
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
                node = PropertyAccessNode(name, prop_token.value)
                if self.current_token.type == TokenType.LBRACKET:
                    self.advance()
                    index_token = self.current_token
                    self.expect(TokenType.INTEGER)
                    if self.current_token.type != TokenType.RBRACKET:
                        raise ParserError("RF2004", "V7 array index must be a single integer literal", self.current_token.line, self.current_token.column)
                    self.advance() # Consumir RBRACKET
                    from .ast_nodes import ArrayIndexNode
                    node = ArrayIndexNode(node, LiteralNode(index_token.value, "INTEGER"))
                    
                    if self.current_token.type == TokenType.LBRACKET:
                        raise ParserError("RF2004", "V7 does not allow chained array indexing", self.current_token.line, self.current_token.column)
                return node
            return IdentifierNode(name) 
        elif token.type == TokenType.EOF:
            raise ParserError("RF2003", "Unexpected EOF, expected expression", token.line, token.column)
        elif token.type == TokenType.LBRACKET:
            self.advance()
            elements = []
            if self.current_token.type != TokenType.RBRACKET:
                elements.append(self.expression())
                while self.current_token.type == TokenType.COMMA:
                    self.advance()
                    elements.append(self.expression())
            self.expect(TokenType.RBRACKET)
            from .ast_nodes import ArrayLiteralNode
            return ArrayLiteralNode(elements)

        raise ParserError("RF2004", f"Invalid expression, unexpected token {token.type}", token.line, token.column)
