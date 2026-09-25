import re
from .tokens import TokenType, Token
from .errors import LexerError

KEYWORDS = {
    "RULE": TokenType.RULE, "LANGUAGE": TokenType.LANGUAGE, "WHEN": TokenType.WHEN,
    "THEN": TokenType.THEN, "ELSE": TokenType.ELSE, "END": TokenType.END,
    "ALLOW": TokenType.ALLOW, "DENY": TokenType.DENY, "NO_ACTION": TokenType.NO_ACTION,
    "ALERT": TokenType.ALERT, "APPLY": TokenType.APPLY, "AND": TokenType.AND,
    "OR": TokenType.OR, "NOT": TokenType.NOT, "IS": TokenType.IS, "NULL": TokenType.NULL,
    "true": TokenType.BOOLEAN, "false": TokenType.BOOLEAN
}

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
            
            # 3. Strings with escapes
            if char == '"':
                self.advance()
                val = ""
                while self.peek() and self.peek() != '"':
                    if self.peek() == '\\':
                        self.advance()
                        esc = self.peek()
                        if esc == '"': val += '"'
                        elif esc == '\\': val += '\\'
                        elif esc == 'n': val += '\n'
                        elif esc == 't': val += '\t'
                        else:
                            raise LexerError("RF1001", f"Unknown escape character '{esc}'", start_line, start_col)
                        self.advance()
                    else:
                        val += self.peek()
                        self.advance()
                if not self.peek():
                    raise LexerError("RF1001", "Unterminated string", start_line, start_col)
                self.advance()
                tokens.append(Token(TokenType.STRING, val, start_line, start_col))
                continue
                
            # 4. Dates & Numbers
            if char.isdigit():
                match = DATE_REGEX.match(self.source, self.pos)
                if match:
                    val = match.group(0)
                    for _ in val: self.advance()
                    tokens.append(Token(TokenType.DATE, val, start_line, start_col))
                    continue
                    
                val = ""
                is_decimal = False
                while self.peek() and (self.peek().isdigit() or self.peek() == '.'):
                    if self.peek() == '.':
                        if is_decimal:
                            raise LexerError("RF1001", "Invalid number format", start_line, start_col)
                        if not self.peek(1) or not self.peek(1).isdigit():
                            break
                        is_decimal = True
                    val += self.peek()
                    self.advance()
                
                if self.peek() == '.' and not is_decimal:
                    raise LexerError("RF1001", "Invalid number format", start_line, start_col)
                    
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
            if char == '=':
                if self.peek(1) == '=':
                    tokens.append(Token(TokenType.EQ, '==', start_line, start_col))
                    self.advance(); self.advance(); continue
                raise LexerError("RF1001", "Invalid character '='", start_line, start_col)
            if char == '!':
                if self.peek(1) == '=':
                    tokens.append(Token(TokenType.NEQ, '!=', start_line, start_col))
                    self.advance(); self.advance(); continue
                raise LexerError("RF1001", "Invalid character '!'", start_line, start_col)
            if char == '>' and self.peek(1) == '=':
                tokens.append(Token(TokenType.GTE, '>=', start_line, start_col))
                self.advance(); self.advance(); continue
            if char == '<' and self.peek(1) == '=':
                tokens.append(Token(TokenType.LTE, '<=', start_line, start_col))
                self.advance(); self.advance(); continue
                
            single_ops = {'>': TokenType.GT, '<': TokenType.LT, '+': TokenType.PLUS, '-': TokenType.MINUS, '*': TokenType.MULTIPLY, '/': TokenType.DIVIDE}
            if char in single_ops:
                tokens.append(Token(single_ops[char], char, start_line, start_col))
                self.advance(); continue
                
            symbols = {'(': TokenType.LPAREN, ')': TokenType.RPAREN, '.': TokenType.DOT, ',': TokenType.COMMA}
            if char in symbols:
                tokens.append(Token(symbols[char], char, start_line, start_col))
                self.advance(); continue
                
            raise LexerError("RF1001", f"Invalid character '{char}'", start_line, start_col)
            
        tokens.append(Token(TokenType.EOF, None, self.line, self.column))
        return tokens
