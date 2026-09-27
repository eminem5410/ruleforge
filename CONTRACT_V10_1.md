# RuleForge V10.1 — Rich Array Operations (ANY / ALL)

This document defines the normative specification for evaluating conditions over array elements without introducing general-purpose lambdas or loops.

## 1. Syntax
```text
ANY <array_expression> WHERE <boolean_expression>
ALL <array_expression> WHERE <boolean_expression>
2. Contextual Variable (it)
Inside the <boolean_expression>, the special identifier it is bound to the current array element being evaluated.

If the array is Array<T>, it has type T.
it can be used to access properties (e.g., it.total > 100) or for direct comparisons (e.g., it == "vip").
3. Semantics & Short-Circuiting
ANY: Returns true as soon as one element evaluates to true. Returns false if the array is empty or no element matches.
ALL: Returns false as soon as one element evaluates to false. Returns true if the array is empty or all elements match.
4. Typing
<array_expression> must evaluate to an Array<T>. Otherwise, throws RF3003.
<boolean_expression> must evaluate to Boolean. Otherwise, throws RF3003.
5. Compiler Boundary
The V9 Compiler does not natively compile ANY/ALL to LINQ/Python comprehensions. It safely falls back to the Interpreter for rules containing these nodes, preserving semantics.
