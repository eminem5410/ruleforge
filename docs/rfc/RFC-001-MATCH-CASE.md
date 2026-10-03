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
