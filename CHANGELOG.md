# RuleForge Changelog

## V11.8.x - Runtime Profiling & Structural Optimizations (Frozen)

**Status:** Frozen. The tree-walking interpreter has reached its design limit in Python. Further micro-optimizations yield diminishing returns and increase risk.

### V11.8.6 - Static Dispatch Investigation (Tag: v11.8.6)
- Replaced instance-level bound methods dispatch with a module-level static `_DISPATCHERS` table.
- **Result:** No significant end-to-end performance improvement.
- **Conclusion:** Bound method creation was not the primary bottleneck. Investigation closed.

### V11.8.5 - Context Isolation & Safe Deepcopy (Tag: v11.8.5)
- Refactored `FILTER`, `MAP`, and `ANY/ALL` to use an internal `_it_stack` instead of mutating the user's context dictionary.
- Added `try/finally` to ensure stack integrity during runtime errors.
- Enabled safe conditional `deepcopy`: read-only rules now bypass `deepcopy(context)` entirely.

### V11.8.4 - O(1) AST Evaluator Dispatch (Tag: v11.8.4)
- Eliminated the `isinstance()` chain in `_eval_node_impl`.
- Replaced with an O(1) dictionary lookup mapping `type(node)` to handler methods.
- Reduced architectural overhead by ~550,000 function calls per 10k evaluations.

### V11.8.2 / V11.8.3 - BinaryOp & Trace Overhead (Tags: v11.8.2, v11.8.3)
- Replaced string comparison operator dispatch with `operator` module dict lookup.
- Monkey-patched `_mk_trace` to no-op lambdas when `deep_trace=False`.
- **Result:** Minor improvements, semantics unchanged.

### V11.8.1 - Schema Fingerprint (Tag: v11.8.1)
- Precomputed static schema fingerprint in `RuleEngine.__init__` to avoid repeated `repr()` and `sha256()` calls on the cache key.

## V11.7.0 - AST Cache (Tag: v11.7.0)
- Implemented LRU cache for Lexer/Parser/SemanticAnalyzer results.
- Cache key: `sha256(source_code + schema_repr)`
- Achieved ~16x speedup on warm path evaluations.

## V11.6.0 - Compiler Cleanup (Tag: v11.6.0)
- Extracted shared compiler logic.
- Eliminated O(N²) compiler pipeline evaluation.
- Froze interpreter/compiler equivalence (61/61 conformance).
