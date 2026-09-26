# RuleForge Language Specification - Arrays (V7.0.0)

This document defines the semantic contract for Array support in RuleForge Language Version 2.
RuleForge remains a declarative, deterministic, and sandboxed DSL. Arrays are introduced to support multi-valued context properties and collection checks, not to become a general-purpose programming language.

## 1. Design Principles
- **Strict Homogeneity:** Arrays must contain elements of exactly one primitive type.
- **Immutability:** Arrays are immutable values. There are no mutation operations (push, pop, assign).
- **Bounded Execution:** No loops, iterators, or higher-order functions (map, filter, reduce) are allowed. Evaluation is strictly O(1) for access and O(N) for specific built-in functions (LENGTH, CONTAINS), bounded by the AST execution limits.

## 2. Type System
V7 introduces the `Array<T>` type.
- `Array<Integer>`
- `Array<Decimal>`
- `Array<String>`
- `Array<Boolean>`
- `Array<Date>`

Arrays of Arrays (nested arrays) are explicitly forbidden in V7.

### 2.1 Homogeneity Enforcement
- `[1, 2, 3]` evaluates to `Array<Integer>`.
- `["A", "B"]` evaluates to `Array<String>`.
- `[1, "A"]` results in a Semantic Error (`RF3xxx`) due to type mismatch.
- `[]` (empty array literal) evaluates to `Array<Null>` and can be implicitly cast to any `Array<T>` expected by a function or context property.

## 3. Context Integration
Arrays can be provided via the runtime context, just like primitive types.
- Context Schema: `"customer": { "tags": "Array<String>" }`
- Context Data: `"customer": { "tags": ["vip", "premium"] }`

## 4. Syntax & Operators

### 4.1 Array Literals
Enclosed in square brackets, separated by commas.
`[1, 2, 3]`

### 4.2 Indexing (Property Access)
Arrays are 0-indexed. Indexing is performed using the dot notation property access, followed by the index in brackets.
- `customer.tags[0]`
- Only Integer literals are allowed as indices. Dynamic expressions (`customer.tags[someVar]`) are not allowed in V7.

## 5. Built-in Functions
V7 extends the standard library with two array-specific functions.

### 5.1 `LENGTH(array)`
- **Signature:** `LENGTH(Array<T>) -> Integer`
- **Description:** Returns the number of elements in the array.
- **Errors:**
  - `LENGTH(NULL)` -> Runtime Type Error (`RF4002`). NULL is not an array.
  - `LENGTH([])` -> 0.
- **Type Safety:** Argument must evaluate to `Array<T>`.

### 5.2 `CONTAINS(array, value)`
- **Signature:** `CONTAINS(Array<T>, T) -> Boolean`
- **Description:** Returns `true` if the `value` exists in the `array`, `false` otherwise.
- **Errors:**
  - `CONTAINS(NULL, value)` -> Runtime Type Error (`RF4002`).
  - `CONTAINS(array, NULL)` -> Semantic Error (`RF3xxx`). Searching for NULL is forbidden.
- **Type Safety:** The type of `value` must match the inner type `T` of the `array`.
  - `CONTAINS(["admin", "user"], "admin")` -> Boolean
  - `CONTAINS(["admin", "user"], 123)` -> Semantic Error (`RF3xxx`). Integer does not match String.

## 6. Runtime & NULL Semantics
RuleForge's strict NULL semantics extend to arrays:
- Accessing an index on a `NULL` array (e.g., `customer.tags[0]` where `tags` is `NULL`) -> Runtime Type Error (`RF4002`).
- Accessing an index out of bounds (e.g., `arr[5]` on a 3-element array) -> Runtime Type Error (`RF4002`).

## 7. Forbidden Features (Non-Goals for V7)
To maintain the language's deterministic and bounded-execution guarantees, the following are explicitly forbidden:
- Array mutation (`arr[0] = 5`)
- Slicing (`arr[1:3]`)
- Nested arrays (`[[1, 2], [3, 4]]`)
- Array equality (`arr1 == arr2`)
- Higher-order functions (`MAP`, `FILTER`, `ANY`, `ALL`, `REDUCE`)
- Lambdas / Anonymous functions
