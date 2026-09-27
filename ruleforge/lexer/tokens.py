class TokenType:
    # Keywords
    RULE="RULE"; LANGUAGE="LANGUAGE"; WHEN="WHEN"; THEN="THEN"; ELSE="ELSE"; END="END"
    ALLOW="ALLOW"; DENY="DENY"; NO_ACTION="NO_ACTION"; ALERT="ALERT"; APPLY="APPLY"
    AND="AND"; OR="OR"; NOT="NOT"; IS="IS"; NULL="NULL"
    
    # Literals
    IDENTIFIER="IDENTIFIER"; INTEGER="INTEGER"; DECIMAL="DECIMAL"; STRING="STRING"; BOOLEAN="BOOLEAN"; DATE="DATE"; EMIT="EMIT"; WITH="WITH"
    
    # Operators
    EQ="=="; NEQ="!="; GT=">"; LT="<"; GTE=">="; LTE="<="
    PLUS="+"; MINUS="-"; MULTIPLY="*"; DIVIDE="/"
    
    # Symbols
    LPAREN="("; RPAREN=")"; DOT="."; COMMA=","
    LBRACKET="["; RBRACKET="]"
    
    # Control
    EOF="EOF"

class Token:
    def __init__(self, type, value, line, column):
        self.type=type; self.value=value; self.line=line; self.column=column
    def __repr__(self): return f"Token({self.type}, '{self.value}', L:{self.line}, C:{self.column})"
