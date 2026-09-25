import re
from .tokens import TokenType, Token

KEYWORDS = {
    "RULE": TokenType.RULE, "LANGUAGE": TokenType.LANGUAGE, "WHEN": TokenType.WHEN,
    "THEN": TokenType.THEN, "ELSE": TokenType.ELSE, "END": TokenType.END,
    "ALLOW": TokenType.ALLOW, "DENY": TokenType.DENY, "NO_ACTION": TokenType.NO_ACTION,
    "ALERT": TokenType.ALERT, "APPLY": TokenType.APPLY, "AND": TokenType.AND,
    "OR": TokenType.OR, "NOT": TokenType.NOT, "IS": TokenType.IS, "NULL": TokenType.NULL,
    "true": TokenType.BOOLEAN, "false": TokenType.BOOLEAN
}

# Regex para Fecha (YYYY-MM-DD)
DATE_REGEX = re.compile(r'\d{4}-\d{2}-\d{2}')

class Lexer:
    def __init__(self, source):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1

    def advance(self):
        if self.pos < len(self.source):
            if self.source[self.pos] == '\n':
                self.line += 1
                self.column = 1
            else:
                self.column += 1
            self.pos += 1

    def peek(self, offset=0):
        pos = self.pos + offset
        return self.source[pos] if pos < len(self.source) else None

    def tokenize(self):
        tokens = []
        while self.pos < len(self.source):
            char = self.peek()
            
            # 1. Whitespace
            if char.isspace():
                self.advance()
                continue
                
            # 2. Comments (// ...)
            if char == '/' and self.peek(1) == '/':
                while self.peek() and self.peek() != '\n':
                    self.advance()
                continue
                
            start_line, start_col = self.line, self.column
            
            # 3. Strings
            if char == '"':
                self.advance()
                val = ""
                while self.peek() and self.peek() != '"':
                    val += self.peek()
                    self.advance()
                if not self.peek():
                    raise Exception(f"RF1001 Lexical Error: Unterminated string at Line {start_line}, Column {start_col}")
                self.advance() # Consumir comilla final
                tokens.append(Token(TokenType.STRING, val, start_line, start_col))
                continue
                
            # 4. Dates & Numbers (Longest match para fechas)
            if char.isdigit():
                # Intentar matchear Fecha primero
                match = DATE_REGEX.match(self.source, self.pos)
                if match:
                    val = match.group(0)
                    for _ in val: self.advance()
                    tokens.append(Token(TokenType.DATE, val, start_line, start_col))
                    continue
                    
                # Si no es fecha, es numero
                val = ""
                is_decimal = False
                while self.peek() and (self.peek().isdigit() or self.peek() == '.'):
                    if self.peek() == '.':
                        if is_decimal:
                            raise Exception(f"RF1001 Lexical Error: Invalid number format at Line {start_line}, Column {start_col}")
                        # Check si el punto es seguido por un digito (para no romper customer.age)
                        if not self.peek(1) or not self.peek(1).isdigit():
                            break
                        is_decimal = True
                    val += self.peek()
                    self.advance()
                
                # Si terminó en un punto y no siguió como decimal (ej: 1.)
                if self.peek() == '.' and not is_decimal:
                    raise Exception(f"RF1001 Lexical Error: Invalid number format at Line {start_line}, Column {start_col}")
                    
                tt = TokenType.DECIMAL if is_decimal else TokenType.INTEGER
                tokens.append(Token(tt, val, start_line, start_col))
                continue
                
            # 5. Identifiers & Keywords
            if char.isalpha() or char == '_':
                val = ""
                while self.peek() and (self.peek().isalnum() or self.peek() == '_'):
                    val += self.peek()
                    self.advance()
                tt = KEYWORDS.get(val, TokenType.IDENTIFIER)
                tokens.append(Token(tt, val, start_line, start_col))
                continue
                
            # 6. Operators (Longest Match)
            if char == '=' and self.peek(1) == '=':
                tokens.append(Token(TokenType.EQ, '==', start_line, start_col))
                self.advance(); self.advance(); continue
            if char == '!' and self.peek(1) == '=':
                tokens.append(Token(TokenType.NEQ, '!=', start_line, start_col))
                self.advance(); self.advance(); continue
            if char == '>' and self.peek(1) == '=':
                tokens.append(Token(TokenType.GTE, '>=', start_line, start_col))
                self.advance(); self.advance(); continue
            if char == '<' and self.peek(1) == '=':
                tokens.append(Token(TokenType.LTE, '<=', start_line, start_col))
                self.advance(); self.advance(); continue
                
            # Single Char Operators
            single_ops = {'>': TokenType.GT, '<': TokenType.LT, '+': TokenType.PLUS, '-': TokenType.MINUS, '*': TokenType.MULTIPLY, '/': TokenType.DIVIDE}
            if char in single_ops:
                tokens.append(Token(single_ops[char], char, start_line, start_col))
                self.advance(); continue
                
            # 7. Symbols
            symbols = {'(': TokenType.LPAREN, ')': TokenType.RPAREN, '.': TokenType.DOT, ',': TokenType.COMMA}
            if char in symbols:
                tokens.append(Token(symbols[char], char, start_line, start_col))
                self.advance(); continue
                
            # 8. Invalid Character
            raise Exception(f"RF1001 Lexical Error: Invalid character '{char}' at Line {start_line}, Column {start_col}")
            
        tokens.append(Token(TokenType.EOF, None, self.line, self.column))
        return tokens
