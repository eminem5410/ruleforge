from .lexer import TokenType, Lexer
from .ast_nodes import *

class Parser:
    def __init__(self, tokens):
        self.tokens=tokens; self.pos=0; self.current_token=self.tokens[self.pos]
    def advance(self):
        self.pos+=1
        if self.pos<len(self.tokens): self.current_token=self.tokens[self.pos]
    def expect(self, token_type):
        if self.current_token.type==token_type: self.advance()
        else: raise Exception(f"RF2001 Parse Error: Expected {token_type} but got {self.current_token.type} at L:{self.current_token.line} C:{self.current_token.column}")
    def parse(self):
        rules=[]
        while self.current_token.type!=TokenType.EOF: rules.append(self.parse_single_rule())
        return rules
    def parse_single_rule(self):
        self.expect(TokenType.RULE); rule_name=self.current_token.value; self.expect(TokenType.IDENTIFIER)
        self.expect(TokenType.WHEN); when_expr=self.expression()
        self.expect(TokenType.THEN); then_action=self.action()
        else_action=None
        if self.current_token.type==TokenType.ELSE: self.advance(); else_action=self.action()
        self.expect(TokenType.END)
        return RuleNode(rule_name,when_expr,then_action,else_action)
    def action(self):
        token=self.current_token
        if token.type in [TokenType.ALLOW,TokenType.NO_ACTION]: self.advance(); return ActionNode(token.value)
        elif token.type in [TokenType.DENY,TokenType.ALERT,TokenType.APPLY]:
            self.advance(); val_token=self.current_token; self.expect(TokenType.STRING); return ActionNode(token.value,val_token.value)
        raise Exception(f"RF2001 Parse Error: Expected action but got {token.type} at L:{token.line}")
    def expression(self):
        node=self.comparison()
        while self.current_token.type in [TokenType.AND,TokenType.OR]:
            op=self.current_token.value; self.advance(); node=BinaryOpNode(node,op,self.comparison())
        return node
    def comparison(self):
        node=self.primary()
        if self.current_token.type==TokenType.IS:
            self.advance(); is_not=False
            if self.current_token.type==TokenType.NOT: self.advance(); is_not=True
            self.expect(TokenType.NULL); return NullCheckNode(node,is_not)
        while self.current_token.type in [TokenType.EQ,TokenType.NEQ,TokenType.GT,TokenType.LT,TokenType.GTE,TokenType.LTE]:
            op=self.current_token.value; self.advance(); node=BinaryOpNode(node,op,self.primary())
        return node
    def primary(self):
        token=self.current_token
        if token.type in [TokenType.INTEGER,TokenType.DECIMAL,TokenType.STRING,TokenType.BOOLEAN]:
            self.advance(); return LiteralNode(token.value,token.type)
        elif token.type==TokenType.IDENTIFIER:
            name=token.value; self.advance()
            if self.current_token.type==TokenType.LPAREN:
                self.advance(); args=[]
                if self.current_token.type!=TokenType.RPAREN:
                    args.append(self.expression())
                    while self.current_token.type==TokenType.COMMA: self.advance(); args.append(self.expression())
                self.expect(TokenType.RPAREN); return FunctionCallNode(name,args)
            elif self.current_token.type==TokenType.DOT:
                self.advance(); prop_token=self.current_token; self.expect(TokenType.IDENTIFIER); return PropertyAccessNode(name,prop_token.value)
            return LiteralNode(token.value,token.type)
        raise Exception(f"RF2001 Parse Error: Unexpected token {token.type} at L:{token.line}")
