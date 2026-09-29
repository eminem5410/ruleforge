# RuleForge V11.2 — Deep AST Trace

## Objetivo
Agregar trazabilidad de la evaluación de la expresión WHEN a nivel de nodo AST, permitiendo reconstruir el camino lógico que produjo el resultado de la regla.

## Activación
- `trace=False`: Comportamiento actual, sin generación de EvaluationTrace.
- `trace=True`: Generación de EvaluationTrace para cada regla evaluada.

## Alcance
Se traza exclusivamente la expresión WHEN. No se trazan parser, semantic analyzer, compiler internals, acciones, host effects, adapter operations, timing/profiling ni logging/I/O.

## Estructura
RuleTraceEntry
├── RuleName
├── RuleIndex
├── Matched
├── AppliedPatches[]
├── Actions[]
└── EvaluationTrace?

EvaluationTrace
├── NodeType
├── Operator?
├── Value
├── Type
├── Children[]
├── ShortCircuited
├── ErrorCode?
└── ErrorMessage?

## Semántica
- Cada nodo representa una expresión AST evaluada.
- `Value` representa el resultado producido por ese nodo.
- `Type` representa el tipo RuleForge del resultado.
- `Value` debe tener representación serializable y cross-language estable.

## Short-circuit
Cuando un operador evita evaluar un subárbol:
- `ShortCircuited = true`
- `Value = null`
- El nodo aparece únicamente como marcador estructural. Sus descendientes no se evalúan ni generan trace.
- Aplica a: AND, OR, ANY, ALL.

## Determinismo
El trace representa exactamente el camino de evaluación realizado por el Evaluator. No se generan caminos alternativos.

## Errores
Si un nodo produce un error de evaluación, el nodo registra:
- `ErrorCode`
- `ErrorMessage`
- y `Value = null`.
El error continúa sujeto a las reglas normales de propagación del Evaluator.

## Arrays
- FILTER y MAP generan sus respectivos nodos de trace.
- ANY y ALL registran el short-circuit de acuerdo con la semántica V11.1.
- El binding `it` forma parte del contexto de evaluación, pero no requiere un nodo AST artificial.

## Compiler
El Compiler V9 no instrumenta el AST. Si `trace=True`, la evaluación utiliza el Evaluator interpretado para producir el Deep AST Trace.

## Rendimiento
`trace=False` no debe construir estructuras de trace ni ejecutar lógica adicional de tracing en el camino normal.

## Regla de Oro
El Deep AST Trace es observabilidad de la semántica, no una segunda implementación de la semántica. El trace no decide nada. El Evaluator sigue siendo la autoridad.
