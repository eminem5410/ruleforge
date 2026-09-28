# RuleForge V11.1 — Advanced Array Operations (FILTER / MAP)

## 1. Syntax
```text
FILTER <array_expression> WHERE <boolean_expression>
MAP <array_expression> USING <expression>
2. Contextual Variable (it)
Inside WHERE or USING, it is bound to the current array element.

If the array is Array<T>, it has type T.
3. Semantics & Typing
FILTER
Semantics: Returns Array<T> containing only elements where <boolean_expression> is true.
Typing: <array_expression> must be Array<T>. <boolean_expression> must be Boolean. Otherwise RF3003 (Invalid array operation type).
Empty: If input is empty, returns empty Array<T>.
MAP
Semantics: Returns a new Array<U> containing the result of <expression> for each element.
Typing: <array_expression> must be Array<T>. U is inferred statically from <expression>.
Empty: If input is empty, returns empty Array<U>. If <array_expression> is an untyped literal [], throws RF3003.
4. Nesting Restriction
Nested FILTER or MAP is NOT supported in V11.1. The semantic analyzer MUST reject nested FILTER/MAP with RF3003.

5. Compiler Boundary
The V9 Compiler does not natively compile FILTER/MAP. It safely falls back to the Interpreter.
