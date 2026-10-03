# RFC-001: MATCH / CASE

**Status:** Draft
**Version:** 0.2
**Target:** V12.0

## 1. Objetivo y Casos de Uso
Permitir la selección de una rama de ejecución basada en la igualdad estricta de un valor, reemplazando estructuras repetitivas de `IF/ELSE IF` sobre la misma propiedad. 

**Caso de uso típico:** Evaluación de estados o categorías (`customer.status`, `order.type`).

## 2. Sintaxis y Alcance (Gramática)
`MATCH` será una construcción de decisión a nivel de regla. No es un statement insertable dentro de un `THEN`, sino que reemplaza la estructura `WHEN/THEN`.

```ebnf
MatchRule       ::= "RULE" Identifier "LANGUAGE" "1" "MATCH" Expression CaseBlock { CaseBlock } [ "DEFAULT" ":" ActionList ] "END"
CaseBlock       ::= "CASE" Literal ":" ActionList
Literal         ::= STRING | INTEGER | DECIMAL | BOOLEAN | DATE
Ejemplo de sintaxis:


RULE customer_status LANGUAGE 1

MATCH customer.status
CASE "ACTIVE":
    ALLOW
CASE "BLOCKED":
    DENY "Blocked"
DEFAULT:
    NO_ACTION
END
3. Invariantes Semánticas
Evaluación Única: La Expression se evalúa exactamente una vez al inicio.
Selección Única: Selecciona como máximo un CASE. No existe fall-through.
Comparación Estricta: Se comparan por igualdad estricta y tipada. No existe coerción implícita (Integer a Decimal, etc.).
Sin Coincidencia: Si ningún CASE coincide y existe DEFAULT, se ejecuta DEFAULT. Si no existe DEFAULT, se ejecuta NO_ACTION.
Prohibición de NULL: NULL no es un Literal válido para CASE. Una expresión que evalúe a NULL en runtime nunca coincide con un CASE (irá a DEFAULT o NO_ACTION).
Ejecución Secuencial: Las acciones de la rama seleccionada se ejecutan secuencialmente. SET mantiene la semántica existente del pipeline (modifica working_context y es visible para reglas siguientes).
Sin Loops/Recursión: No se introducen loops, recursión ni efectos externos.
4. Restricciones y Errores (Validation)
CASE Duplicado: Error semántico. No se permiten dos CASE con el mismo valor literal.
CASE Vacío: Error sintáctico. Un CASE debe tener al menos una acción.
DEFAULT Duplicado: Error sintáctico.
Tipos Incompatibles: Error semántico si el tipo de Expression no coincide con el tipo del Literal.
Nesting: V12.0 no permite anidamiento estructural de MATCH.
5. Límites de Seguridad
MAX_CASES_PER_MATCH: 50 (prevenir explosión del AST y DoS).
6. Contrato de Trace
El trace se adaptará al modelo de trazabilidad existente en V11.8.x. No se introducirán nuevos estados de "Phantom" o "Skipped" artificiales.
TRACE
──────────────────────────────
Rule: customer_status

MATCH customer.status -> "ACTIVE"
  CASE "ACTIVE" -> MATCHED
    Action: ALLOW
  CASE "BLOCKED" -> NOT_EVALUATED
  DEFAULT -> NOT_EVALUATED

RESULT
  ✓ Condition matched
DECISION
  ✓ MATCH
  Actions: ALLOW
──────────────────────────────
7. Matriz de Conformance Inicial (Vectores)
RF-CONF-MATCH-001: Match simple, coincide con el primer CASE.
RF-CONF-MATCH-002: Match simple, coincide con el segundo CASE.
RF-CONF-MATCH-003: Match simple, no coincide, va a DEFAULT.
RF-CONF-MATCH-004: Match simple, no coincide, no hay DEFAULT (NO_ACTION).
RF-CONF-MATCH-005: Match donde Expression evalúa a NULL (va a DEFAULT/NO_ACTION).
RF-CONF-MATCH-006: Error semántico: tipos incompatibles (String vs Integer).
RF-CONF-MATCH-007: Error semántico: CASE duplicado.
RF-CONF-MATCH-008: Match con SET en el CASE, afecta a la siguiente regla en el pipeline.

## 8. MATCH Trace Contract (V12.0.0 Layer 5)

El trace de `MATCH` debe respetar la semántica de evaluación lazy (short-circuit) y no inventar estados de ejecución artificiales (Phantoms) para los `CASEs` que no fueron evaluados.

### 8.1. Reglas de Trazabilidad
1. **Evaluación Única:** La expresión `MATCH` se evalúa exactamente una vez y su valor y tipo se registran en el trace.
2. **Short-Circuit Real:** Si un `CASE` coincide, los `CASEs` posteriores y el `DEFAULT` **no deben ser evaluados**.
3. **Sin Phantoms Artificiales:** Los `CASEs` no evaluados no deben aparecer con `Value: false`. Deben marcarse explícitamente con `ShortCircuited: true` y `Reason: short_circuit`.
4. **DEFAULT:** Si ningún `CASE` coincide, el `DEFAULT` se ejecuta. Los `CASEs` evaluados aparecerán con `Matched: false`.
5. **NO_ACTION:** Si no hay coincidencia y no hay `DEFAULT`, se ejecuta `NO_ACTION`.
6. **SET/EMIT:** Las acciones del `CASE` seleccionado se resuelven y se registran en `Decision.actions` conforme al contrato existente de V11.3. El trace de `MATCH` no crea nodos artificiales para las acciones.
7. **Errores:** Si la expresión `MATCH` o un `CASE` evaluado lanza un error, se conserva el contrato de V11.3 (`_error_trace` en el nodo fallido).

### 8.2. Estructura Conceptual del Trace

Para un match en el primer `CASE`:
```text
MATCH customer.status -> "ACTIVE"
  CASE "ACTIVE" -> MATCHED
  CASE "BLOCKED" -> SHORT_CIRCUITED
  DEFAULT -> SHORT_CIRCUITED
```

Para un match en `DEFAULT` (ningún CASE coincidió):
```text
MATCH customer.status -> "PENDING"
  CASE "ACTIVE" -> EVALUATED_FALSE
  CASE "BLOCKED" -> EVALUATED_FALSE
  DEFAULT -> MATCHED
```

### 8.3. Matriz de Pruebas de Trace (Layer 5 Tests)
- `test_match_trace_first_case`: Verifica que el primer CASE coincida y los demás estén marcados como short-circuited.
- `test_match_trace_second_case`: Verifica que el primer CASE sea false, el segundo coincida, y los demás short-circuited.
- `test_match_trace_default`: Verifica que todos los CASEs sean false y DEFAULT coincida.
- `test_match_trace_no_default`: Verifica que todos los CASEs sean false y se ejecute NO_ACTION.
- `test_match_trace_set`: Verifica que el SET dentro del CASE coincidido se registre en el trace.
- `test_match_trace_error`: Verifica que si la expresión MATCH falla, el trace capture el error en ese nodo.

### 8.4. Restricción Arquitectónica
El trace de `MATCH` debe construirse dentro del bloque `if node.match_node:` en `eval_rule()`.
**No se debe modificar** el dispatch global de `eval_node()` ni las rutas de V11 para acomodar el trace de `MATCH`.
