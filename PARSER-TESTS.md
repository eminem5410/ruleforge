# RuleForge Parser Conformance Tests

## Valid Syntax (Must Produce AST)

### PARSE-001: Basic Rule
Input Tokens: [RULE, IDENTIFIER("test"), LANGUAGE, INTEGER(1), WHEN, IDENTIFIER("active"), EQ, BOOLEAN("true"), THEN, ALLOW, END]
Expected AST: RuleNode(name="test", lang=1, when=BinOp(Prop("active"), ==, Lit("true")), then=[Action(ALLOW)])

### PARSE-002: Multiple Actions
Input: [RULE, IDENTIFIER("r"), LANGUAGE, INTEGER(1), WHEN, BOOLEAN("true"), THEN, DENY, STRING("No"), ALERT, STRING("Check"), END]
Expected AST: RuleNode(then=[Action(DENY, "No"), Action(ALERT, "Check")])

### PARSE-003: Operator Precedence (AND before OR)
Input: [IDENTIFIER("a"), OR, IDENTIFIER("b"), AND, IDENTIFIER("c")]
Expected AST: BinOp(Prop("a"), OR, BinOp(Prop("b"), AND, Prop("c")))

## Invalid Syntax (Must Reject with RF2xxx)

### PARSE-ERR-001: Missing END
Input: [RULE, IDENTIFIER("r"), LANGUAGE, INTEGER(1), WHEN, BOOLEAN("true"), THEN, ALLOW]
Expected: RF2003 Unexpected EOF

### PARSE-ERR-002: Missing Expression
Input: [RULE, IDENTIFIER("r"), LANGUAGE, INTEGER(1), WHEN, THEN, ALLOW, END]
Expected: RF2002 Unexpected Token (Expected Expression, got THEN)

### PARSE-ERR-003: Invalid Action Mix
Input: [RULE, IDENTIFIER("r"), LANGUAGE, INTEGER(1), WHEN, BOOLEAN("true"), THEN, NO_ACTION, ALLOW, END]
Expected: RF2005 Invalid Action (NO_ACTION must be alone)
