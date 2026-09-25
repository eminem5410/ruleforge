class TokenType:
    RULE="RULE"; WHEN="WHEN"; THEN="THEN"; ELSE="ELSE"; END="END"
    AND="AND"; OR="OR"; NOT="NOT"; IS="IS"; NULL="NULL"
    ALLOW="ALLOW"; DENY="DENY"; ALERT="ALERT"; APPLY="APPLY"; NO_ACTION="NO_ACTION"
    IDENTIFIER="IDENTIFIER"; INTEGER="INTEGER"; DECIMAL="DECIMAL"; STRING="STRING"; BOOLEAN="BOOLEAN"
    EQ="=="; NEQ="!="; GT=">"; LT="<"; GTE=">="; LTE="<="
    PLUS="+"; MINUS="-"; MULTIPLY="*"; DIVIDE="/"
    LPAREN="("; RPAREN=")"; DOT="."; COMMA=","; EOF="EOF"

class Token:
    def __init__(self, type, value, line, column):
        self.type=type; self.value=value; self.line=line; self.column=column
    def __repr__(self): return f"Token({self.type}, '{self.value}', L:{self.line}, C:{self.column})"

class Lexer:
    def __init__(self, source_code):
        self.source=source_code; self.pos=0; self.line=1; self.column=1
        self.current_char=self.source[self.pos] if len(self.source)>0 else None

    def advance(self):
        if self.current_char=='\n': self.line+=1; self.column=1
        else: self.column+=1
        self.pos+=1
        self.current_char=self.source[self.pos] if self.pos<len(self.source) else None

    def skip_whitespace(self):
        while self.current_char is not None and self.current_char.isspace(): self.advance()

    def read_string(self):
        start_line,start_col=self.line,self.column; self.advance(); result=""
        while self.current_char is not None and self.current_char!='"':
            result+=self.current_char; self.advance()
        if self.current_char is None: raise Exception(f"RF1001 Lexical Error: Unterminated string at Line {start_line}")
        self.advance(); return Token(TokenType.STRING,result,start_line,start_col)

    def read_number(self):
        result=""; start_line,start_col=self.line,self.column; is_decimal=False
        while self.current_char is not None and (self.current_char.isdigit() or self.current_char=='.'):
            if self.current_char=='.':
                if is_decimal: raise Exception("RF1001 Lexical Error: Invalid decimal")
                is_decimal=True
            result+=self.current_char; self.advance()
        return Token(TokenType.DECIMAL,float(result),start_line,start_col) if is_decimal else Token(TokenType.INTEGER,int(result),start_line,start_col)

    def read_identifier(self):
        result=""; start_line,start_col=self.line,self.column
        while self.current_char is not None and (self.current_char.isalnum() or self.current_char=='_'):
            result+=self.current_char; self.advance()
        keywords={"RULE":TokenType.RULE,"WHEN":TokenType.WHEN,"THEN":TokenType.THEN,"ELSE":TokenType.ELSE,"END":TokenType.END,"AND":TokenType.AND,"OR":TokenType.OR,"NOT":TokenType.NOT,"IS":TokenType.IS,"NULL":TokenType.NULL,"ALLOW":TokenType.ALLOW,"DENY":TokenType.DENY,"ALERT":TokenType.ALERT,"APPLY":TokenType.APPLY,"NO_ACTION":TokenType.NO_ACTION,"true":TokenType.BOOLEAN,"false":TokenType.BOOLEAN}
        return Token(keywords.get(result,TokenType.IDENTIFIER),result,start_line,start_col)

    def get_next_token(self):
        while self.current_char is not None:
            if self.current_char.isspace(): self.skip_whitespace(); continue
            if self.current_char=='"': return self.read_string()
            if self.current_char.isdigit(): return self.read_number()
            if self.current_char.isalpha() or self.current_char=='_': return self.read_identifier()
            if self.current_char=='=' and self.pos+1<len(self.source) and self.source[self.pos+1]=='=': t=Token(TokenType.EQ,'==',self.line,self.column); self.advance(); self.advance(); return t
            if self.current_char=='!' and self.pos+1<len(self.source) and self.source[self.pos+1]=='=': t=Token(TokenType.NEQ,'!=',self.line,self.column); self.advance(); self.advance(); return t
            if self.current_char=='>':
                if self.pos+1<len(self.source) and self.source[self.pos+1]=='=': t=Token(TokenType.GTE,'>=',self.line,self.column); self.advance(); self.advance(); return t
                t=Token(TokenType.GT,'>',self.line,self.column); self.advance(); return t
            if self.current_char=='<':
                if self.pos+1<len(self.source) and self.source[self.pos+1]=='=': t=Token(TokenType.LTE,'<=',self.line,self.column); self.advance(); self.advance(); return t
                t=Token(TokenType.LT,'<',self.line,self.column); self.advance(); return t
            if self.current_char=='+': t=Token(TokenType.PLUS,'+',self.line,self.column); self.advance(); return t
            if self.current_char=='-': t=Token(TokenType.MINUS,'-',self.line,self.column); self.advance(); return t
            if self.current_char=='*': t=Token(TokenType.MULTIPLY,'*',self.line,self.column); self.advance(); return t
            if self.current_char=='/': t=Token(TokenType.DIVIDE,'/',self.line,self.column); self.advance(); return t
            if self.current_char=='(': t=Token(TokenType.LPAREN,'(',self.line,self.column); self.advance(); return t
            if self.current_char==')': t=Token(TokenType.RPAREN,')',self.line,self.column); self.advance(); return t
            if self.current_char=='.': t=Token(TokenType.DOT,'.',self.line,self.column); self.advance(); return t
            if self.current_char==',': t=Token(TokenType.COMMA,',',self.line,self.column); self.advance(); return t
            raise Exception(f"RF1001 Lexical Error: Unexpected character '{self.current_char}' at L:{self.line} C:{self.column}")
        return Token(TokenType.EOF,None,self.line,self.column)

    def tokenize(self):
        tokens=[]
        while True:
            token=self.get_next_token(); tokens.append(token)
            if token.type==TokenType.EOF: break
        return tokens
