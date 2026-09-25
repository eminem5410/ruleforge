# RuleForge Lexer Specification

The Lexer is responsible for converting raw source code text into a stream of tokens. It does not understand grammar or semantics; it only tokenizes.

## 1. Token Model
Each token produced by the lexer must contain:
- `type`: The token category (e.g., RULE, IDENTIFIER, INTEGER).
- `value`: The literal value extracted from the source.
- `line`: The line number where the token starts (1-based).
- `column`: The column number where the token starts (1-based).

## 2. Token Types
Keywords: RULE, LANGUAGE, WHEN, THEN, ELSE, END, ALLOW, DENY, NO_ACTION, ALERT, APPLY, AND, OR, NOT, IS, NULL
Literals: STRING, INTEGER, DECIMAL, BOOLEAN, DATE
Identifiers: IDENTIFIER
Operators: EQ (==), NEQ (!=), GT (>), LT (<), GTE (>=), LTE (<=), PLUS (+), MINUS (-), MULTIPLY (*), DIVIDE (/)
Symbols: LPAREN ((), RPAREN ()), DOT (.), COMMA (,)
Control: EOF (End of File)

## 3. Tokenization Rules
- Whitespace (spaces, tabs, newlines) is skipped and does not produce tokens, but increments line/column counters.
- Keywords are matched exactly as defined in Lexical Conventions.
- Strings are read until the closing double quote. Missing closing quotes result in RF1001 Lexical Error.
- Dates are matched by shape (YYYY-MM-DD). Calendar validity (e.g., month 13) is deferred to the Semantic Analyzer.
- Operators are matched using longest-match (e.g., >= is matched as GTE, not GT followed by EQ).
