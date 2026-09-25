# RuleForge Lexer Conformance Tests

## Valid Tokenization (Must Accept)

### LEX-001: Keyword and Identifier
Input:
RULE customer_check
Expected Tokens:
[RULE, IDENTIFIER("customer_check")]

### LEX-002: Property Access and Operators
Input:
customer.age >= 18
Expected Tokens:
[IDENTIFIER("customer"), DOT, IDENTIFIER("age"), GTE, INTEGER(18)]

### LEX-003: String Literal
Input:
"Credit limit exceeded"
Expected Tokens:
[STRING("Credit limit exceeded")]

## Invalid Tokenization (Must Reject)

### LEX-ERR-001: Invalid Character
Input:
customer @ age
Expected Error: RF1001 Lexical Error: Invalid character '@' at Line 1, Column 9

### LEX-ERR-002: Unterminated String
Input:
DENY "Credit limit exceeded
Expected Error: RF1001 Lexical Error: Unterminated string at Line 1, Column 6

### LEX-ERR-003: Invalid Number Format
Input:
invoice.total = 1.
Expected Error: RF1001 Lexical Error: Invalid number format at Line 1, Column 16
