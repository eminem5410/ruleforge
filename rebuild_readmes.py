#!/usr/bin/env python3
"""
Rebuild README.md (English) and README.es.md (Spanish) from baseline content.

Usage:
    cd ~/ruleforge
    python rebuild_readmes.py
"""
from pathlib import Path

README_EN = r'''# RuleForge

[English](./README.md) | [Español](./README.es.md)

<p align="center">
  <img src="docs/assets/ruleforge-banner.png" alt="RuleForge" width="800">
</p>

<p align="center">
  <strong>Deterministic, typed, sandboxed, and auditable rule execution<br>
  for applications that need predictable policy decisions.</strong>
</p>

<p align="center">
  <img alt="Stable release" src="https://img.shields.io/badge/release-v12.0.0-blue">
  <img alt="Python" src="https://img.shields.io/badge/python-3.8+-green">
  <img alt=".NET" src="https://img.shields.io/badge/.NET-Core-success">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-lightgrey">
  <img alt="Status" src="https://img.shields.io/badge/status-stable-brightgreen">
</p>

---

## Table of Contents

- [Design Principle](#design-principle)
- [Architecture](#architecture)
- [Interpreter and Compiler](#interpreter-and-compiler)
- [Supported Language Features](#supported-language-features)
- [Evaluation Trace](#evaluation-trace)
  - [MATCH Trace Contract](#match-trace-contract)
- [Short-Circuit Evaluation](#short-circuit-evaluation)
- [Security and Runtime Safety](#security-and-runtime-safety)
- [Contract-Driven Development](#contract-driven-development)
- [Cross-Language Architecture](#cross-language-architecture)
- [V12.0.0 Quality Gate](#v1200-quality-gate)
- [Tooling](#tooling)
- [Installation](#installation)
- [Project Structure](#project-structure)
- [Development and Quality Gates](#development-and-quality-gates)
- [Language Evolution Rules](#language-evolution-rules)
- [Roadmap](#roadmap)
- [Architectural Baseline](#architectural-baseline)
- [Release](#release)

---

## Design Principle

> Rules declare **intent**.
> The engine evaluates intent.
> The engine produces decisions and patches.
> The host application performs effects.

This separation is fundamental to RuleForge's security and determinism model. The rule engine never executes side effects directly — it produces structured decisions and patches that the host application is responsible for applying. This guarantees that rule evaluation remains observable, reproducible, and safe to run in sensitive workloads.

---

## Architecture

RuleForge is structured as a layered pipeline. Each layer has a single, well-defined responsibility and produces an artifact consumed by the next layer. This separation enables independent testing, conformance verification, and cross-language parity.

<img src="docs/assets/ruleforge-architecture.png" alt="RuleForge Architecture" width="800">



The compiler provides an optimized execution path while preserving the same observable semantics as the interpreter.

### Components

| Component          | Responsibility                                                                                       |
|--------------------|-------------------------------------------------------------------------------------------------------|
| **Lexer**          | Tokenizes RuleForge source code.                                                                      |
| **Parser**         | Builds the Abstract Syntax Tree using recursive descent parsing.                                     |
| **Semantic Analyzer** | Validates rule structure, types, operators, functions, context properties, MATCH/CASE compatibility, duplicate CASE values, and execution constraints against the supplied schema and language contract. |
| **Evaluator**     | Executes the AST under RuleForge's deterministic runtime model.                                       |
| **Compiler**       | Provides optimized condition execution while preserving interpreter semantics.                       |
| **Engine**         | Coordinates parsing, semantic validation, evaluation, sequential state updates, decision generation, tracing, patches, and runtime error handling. |

---

## Interpreter and Compiler

RuleForge maintains two execution paths. Both are required to preserve semantic equivalence — any divergence between them is treated as a release-blocking defect.

```text
Rule Source
     |
     +------------------+
     |                  |
     v                  v
 Interpreter         Compiler
     |                  |
     +--------+---------+
              |
              v
        Observable Result
```

**V11.5** removed an unnecessary quadratic evaluation pattern from the compiled pipeline by introducing direct per-rule execution through:

```python
execute_single(rule, working_context)
```

This preserved sequential `SET` semantics while avoiding repeated evaluation of the complete rule set.

**V12.0.0** builds on that execution architecture.

---

## Supported Language Features

Current RuleForge language support includes:

- Boolean expressions
- Integer arithmetic
- Decimal arithmetic
- String operations
- Date operations
- Property access
- Null checks
- Unary operators
- Binary operators
- `AND` / `OR` short-circuit evaluation
- Function calls
- Array literals
- Array indexing
- `ANY`, `ALL`, `FILTER`, `MAP`
- `SET`, `EMIT`
- `MATCH`, `CASE`, `DEFAULT`
- Structured evaluation traces
- Deep AST tracing
- Runtime execution limits
- Schema-aware validation

---

## Evaluation Trace

Tracing is part of the RuleForge observability contract.

A trace can describe the evaluation of expressions and decisions without changing the underlying semantics. This makes traces safe to ship to logs, audit pipelines, and debugging tools without risking behavioral divergence between traced and untraced execution.

| Field            | Description                              |
|------------------|------------------------------------------|
| `NodeType`       | Canonical AST node type                  |
| `Operator`       | Operator or function                     |
| `Value`          | Serialized result                       |
| `Type`           | RuleForge type                           |
| `Children`       | Evaluated child expressions              |
| `ShortCircuited` | Whether evaluation was skipped           |
| `ErrorCode`      | Runtime error code                       |
| `ErrorMessage`   | Runtime error message                    |

### MATCH Trace Contract

For `MATCH`:

- The `MATCH` expression is evaluated exactly once.
- Its resulting value and type are recorded.
- `CASE` expressions are evaluated sequentially.
- Evaluation stops at the first match.
- Later `CASE` branches are represented as short-circuited rather than falsely evaluated.
- If no `CASE` matches, `DEFAULT` is selected when present.
- If no `CASE` matches and no `DEFAULT` exists, the rule produces `NO_ACTION`.
- `SET` and `EMIT` remain actions rather than artificial trace nodes.
- Runtime errors preserve the established error trace contract.

This behavior is defined in [`docs/rfc/RFC-001-MATCH-CASE.md`](docs/rfc/RFC-001-MATCH-CASE.md).

---

## Short-Circuit Evaluation

RuleForge explicitly models short-circuit behavior. This is part of the language contract, not an optimization — the runtime guarantees that skipped branches are not evaluated and that their omission is observable in the trace.

For `A AND B`, when `A` is false, `B` is not evaluated.

The trace records the skipped branch as:

```json
{
  "ShortCircuited": true,
  "Reason": "short_circuit"
}
```

The same principle applies to supported short-circuiting constructs such as `AND`, `OR`, `ANY`, `ALL`, and `MATCH` branch selection.

---

## Security and Runtime Safety

RuleForge is intentionally constrained. The language is designed for environments where predictability matters more than expressiveness — policy evaluation, compliance, fraud detection, and similar workloads where a non-deterministic result is a defect, not a performance concern.

The execution model provides:

- Bounded execution
- Strict typing
- AST safety limits
- Controlled action semantics
- Schema-aware validation
- No direct external side effects
- Deterministic evaluation
- Runtime error codes
- Traceable execution

> The language is **not** intended to be Turing-complete.
> This is a deliberate design decision.
> Predictability is treated as a language invariant rather than an optimization.

---

## Contract-Driven Development

RuleForge evolves through explicit contracts and RFCs. Every non-trivial behavior is documented before it is implemented, and every implementation is held accountable to its contract through conformance vectors.

Historical contracts include `CONTRACT_V8.md` through `CONTRACT_V11_4.md`.

**V12.0.0** introduces:

```
docs/rfc/RFC-001-MATCH-CASE.md
```

The architectural state of the stable release is documented in:

```
docs/architecture/V12.0.0-BASELINE.md
```

---

## Cross-Language Architecture

RuleForge has independent Python and C# implementations operating against the same language contracts.

The objective is **not** merely API compatibility. The implementations must agree on parsing behavior, semantic validation, decisions, errors, patches, traces, and compiler behavior.

Cross-language conformance is therefore treated as a **release gate** — a release is not cut if Python and C# disagree on any observed behavior in the conformance vectors.

---

## V12.0.0 Quality Gate

The stable V12.0.0 release was validated through multiple independent layers. Each layer is a separate gate; failure in any one blocks the release.

| Validation                       | Result              |
|----------------------------------|---------------------|
| Python Core + Conformance        | 361 passed, 1 skipped |
| C# Core                          | 158/158             |
| C# API                           | 18/18               |
| Cross-language conformance       | 69/69 MATCH         |
| Compiler conformance             | 69/69 MATCH         |
| MATCH/CASE vectors               | 8/8                 |
| MATCH trace tests                | 6/6                 |
| Interpreter/Compiler parity      | 5/5                 |

Cross-language and compiler conformance: **69 / 69 MATCH (100%)**.

MATCH/CASE conformance:

- 6 valid vectors
- 2 invalid vectors
- 8 / 8 validated

The release also preserves the V11 regression suite.

---

## Tooling

RuleForge provides a CLI for validation, evaluation, and tracing.

**Evaluate:**

```bash
ruleforge eval rules.rf --context '{"customer":{"age":25}}'
```

**Validate:**

```bash
ruleforge check rules.rf --schema '{"customer":{"age":"Integer"}}'
```

**Trace:**

```bash
ruleforge trace rules.rf --context '{"customer":{"age":25}}'
```

**Help:**

```bash
ruleforge --help
```

---

## Installation

Install from PyPI (recommended):

```bash
pip install ruleforge-engine
```

Or clone and develop:

```bash
git clone https://github.com/eminem5410/ruleforge.git
cd ruleforge
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

The project also contains the .NET implementation and conformance infrastructure.

---

## Project Structure

```text
ruleforge/
|
+-- ruleforge/
|   +-- lexer/
|   +-- parser/
|   +-- semantic/
|   +-- evaluator/
|   +-- compiler/
|   +-- api/
|   +-- engine.py
|
+-- dotnet/
|   +-- src/
|   |   +-- RuleForge.Core/
|   |   +-- RuleForge.Api/
|   |   +-- RuleForge.ConformanceRunner/
|   |
|   +-- tests/
|
+-- tests/
|   +-- conformance/
|   +-- property/
|   +-- test_evaluator.py
|   +-- test_engine.py
|   +-- test_trace.py
|   +-- test_sequential_semantics.py
|
+-- docs/
|   +-- rfc/
|   +-- architecture/
|
+-- CONTRACT_*.md
+-- README.md
+-- README.es.md
```

---

## Development and Quality Gates

RuleForge follows a layered validation strategy. Each layer gates the next — a regression at any level prevents progression to the subsequent layer.

```text
Python tests
      |
      v
C# Core tests
      |
      v
C# API tests
      |
      v
Cross-language conformance
      |
      v
Compiler conformance
      |
      v
Release gate
```

> A language feature is **not** considered complete until its behavior is validated across the relevant implementation layers.

---

## Language Evolution Rules

Future language changes follow these principles:

| Principle                  | Description                                                                                          |
|----------------------------|------------------------------------------------------------------------------------------------------|
| **RFC First**              | Non-trivial language features are specified before implementation.                                   |
| **Layer by Layer**         | Lexer → AST → Semantic → Evaluator → Trace.                                                         |
| **Cross-Language Parity**  | Python and C# must agree on observable behavior.                                                     |
| **V11/V12 Isolation**      | New features should avoid unnecessary global changes to established execution paths.                |
| **Conformance as a Gate** | A feature is not complete until its behavior is represented in conformance vectors and tests.       |

---

## Roadmap

### Completed

- **V11.0** — ANY / ALL
- **V11.1** — FILTER / MAP
- **V11.2** — Deep AST Trace
- **V11.3** — Trace Contract Hardening
- **V11.4** — Runtime Safety & Determinism
- **V11.5** — Compiler Performance & Sequential Runtime Semantics
- **V11.7** — AST Cache
- **V11.8** — Runtime and trace performance work
- **V11.9** — CLI, REPL, tooling, and API decoupling
- **V12.0** — MATCH / CASE

### Future Considerations

Potential future work includes JSON Schema integration, additional language expressiveness, pattern matching, and further compiler/runtime optimization.

> A general-purpose looping construct such as `FOR EACH` remains deliberately deferred because it would require revisiting RuleForge's bounded, non-Turing-complete execution model.

> Future items are design considerations, **not commitments** to a specific release.

---

## Development Setup

To regenerate visual assets and READMEs from the baseline content:

```bash
# 1. Create the local environment
python3 -m venv .venv
.venv/bin/pip install playwright
.venv/bin/playwright install chromium

# 2. Generate PNG assets (logo, banner, architecture diagram, OG image)
.venv/bin/python build_ruleforge_assets.py

# 3. Regenerate README.md and README.es.md
.venv/bin/python rebuild_readmes.py
```

The `.venv/` directory is gitignored. Each contributor must create their own local environment after cloning.

---

## Architectural Baseline

The stable V12.0.0 architecture is frozen and documented in:

```
docs/architecture/V12.0.0-BASELINE.md
```

This document records:

- V11.8 → V12.0 evolution
- RFC-001 invariants
- Architectural integration
- Trace contract
- Quality gate results
- Discarded decisions
- Future considerations
- Rules for future language evolution

---

## Release

**Current stable release:** `v12.0.0`

---

<p align="center">
  <sub>RuleForge — Deterministic rule execution for predictable policy decisions.</sub>
</p>
'''

README_ES = r'''# RuleForge

[English](./README.md) | [Español](./README.es.md)

<p align="center">
  <img src="docs/assets/ruleforge-banner.png" alt="RuleForge" width="800">
</p>

<p align="center">
  <strong>Ejecución de reglas determinista, tipada, aislada y auditable<br>
  para aplicaciones que necesitan decisiones de política predecibles.</strong>
</p>

<p align="center">
  <img alt="Release estable" src="https://img.shields.io/badge/release-v12.0.0-blue">
  <img alt="Python" src="https://img.shields.io/badge/python-3.8+-green">
  <img alt=".NET" src="https://img.shields.io/badge/.NET-Core-success">
  <img alt="Licencia" src="https://img.shields.io/badge/licencia-MIT-lightgrey">
  <img alt="Estado" src="https://img.shields.io/badge/estado-estable-brightgreen">
</p>

---

## Tabla de contenidos

- [Principio de diseño](#principio-de-diseño)
- [Arquitectura](#arquitectura)
- [Intérprete y compilador](#intérprete-y-compilador)
- [Funcionalidades del lenguaje](#funcionalidades-del-lenguaje)
- [Evaluation Trace](#evaluation-trace)
  - [Contrato de trace para MATCH](#contrato-de-trace-para-match)
- [Short-Circuit](#short-circuit)
- [Seguridad y Runtime Safety](#seguridad-y-runtime-safety)
- [Desarrollo basado en contratos](#desarrollo-basado-en-contratos)
- [Arquitectura Cross-Language](#arquitectura-cross-language)
- [Quality Gate V12.0.0](#quality-gate-v1200)
- [Tooling](#tooling)
- [Instalación](#instalación)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Desarrollo y Quality Gates](#desarrollo-y-quality-gates)
- [Reglas para la evolución del lenguaje](#reglas-para-la-evolución-del-lenguaje)
- [Roadmap](#roadmap)
- [Architectural Baseline](#architectural-baseline)
- [Release](#release)

---

## Principio de diseño

> Las reglas declaran **intención**.
> El motor evalúa la intención.
> El motor produce decisiones y parches.
> La aplicación anfitriona ejecuta los efectos.

Esta separación es fundamental para el modelo de seguridad y determinismo de RuleForge. El motor de reglas nunca ejecuta efectos secundarios directamente — produce decisiones y parches estructurados cuya aplicación es responsabilidad de la aplicación anfitriona. Esto garantiza que la evaluación de reglas sea observable, reproducible y segura de ejecutar en cargas sensibles.

---

## Arquitectura

RuleForge está estructurado como un pipeline por capas. Cada capa tiene una única responsabilidad bien definida y produce un artefacto consumido por la siguiente capa. Esta separación habilita testing independiente, verificación de conformidad y paridad cross-language.

<img src="docs/assets/ruleforge-architecture.png" alt="RuleForge Architecture" width="800">



El compilador proporciona una ruta de ejecución optimizada preservando la misma semántica observable que el intérprete.

### Componentes

| Componente          | Responsabilidad                                                                                              |
|----------------------|---------------------------------------------------------------------------------------------------------------|
| **Lexer**            | Tokeniza el código fuente de RuleForge.                                                                       |
| **Parser**           | Construye el Abstract Syntax Tree mediante _recursive descent parsing_.                                       |
| **Semantic Analyzer** | Valida estructura, tipos, operadores, funciones, propiedades del contexto, compatibilidad MATCH/CASE, valores CASE duplicados y restricciones de ejecución contra el _schema_ y el contrato del lenguaje. |
| **Evaluator**        | Ejecuta el AST bajo el modelo de runtime determinista de RuleForge.                                            |
| **Compiler**         | Proporciona ejecución optimizada de condiciones preservando la semántica del intérprete.                      |
| **Engine**           | Coordina parsing, validación semántica, evaluación, actualizaciones secuenciales del estado, decisiones, tracing, patches y errores de runtime. |

---

## Intérprete y compilador

RuleForge mantiene dos rutas de ejecución. Ambas deben preservar equivalencia semántica — cualquier divergencia entre ellas se trata como un defecto que bloquea el release.

```text
Rule Source
     |
     +------------------+
     |                  |
     v                  v
 Interpreter         Compiler
     |                  |
     +--------+---------+
              |
              v
        Observable Result
```

**V11.5** eliminó un patrón de evaluación cuadrática innecesario del pipeline compilado mediante ejecución directa por regla:

```python
execute_single(rule, working_context)
```

Esto preservó la semántica secuencial de `SET` evitando reevaluar todo el conjunto de reglas.

**V12.0.0** se construye sobre esa arquitectura de ejecución.

---

## Funcionalidades del lenguaje

RuleForge actualmente soporta:

- Expresiones booleanas
- Aritmética de enteros
- Aritmética decimal
- Operaciones de strings
- Operaciones con fechas
- Acceso a propiedades
- Comprobaciones de null
- Operadores unarios
- Operadores binarios
- Evaluación `AND` / `OR` con _short-circuit_
- Llamadas a funciones
- Arrays literales
- Indexación de arrays
- `ANY`, `ALL`, `FILTER`, `MAP`
- `SET`, `EMIT`
- `MATCH`, `CASE`, `DEFAULT`
- Trazas estructuradas
- Deep AST tracing
- Límites de ejecución
- Validación basada en _schema_

---

## Evaluation Trace

Las trazas forman parte del contrato de observabilidad de RuleForge.

Una traza puede describir la evaluación de expresiones y decisiones sin alterar su semántica. Esto permite enviar trazas a logs, pipelines de auditoría y herramientas de debugging sin riesgo de divergencia entre la ejecución con y sin traza.

| Campo            | Descripción                              |
|------------------|------------------------------------------|
| `NodeType`       | Tipo canónico del nodo AST                |
| `Operator`       | Operador o función                       |
| `Value`          | Resultado serializado                    |
| `Type`           | Tipo RuleForge                           |
| `Children`       | Expresiones hijas evaluadas              |
| `ShortCircuited` | Indica si la evaluación fue omitida      |
| `ErrorCode`      | Código de error de runtime               |
| `ErrorMessage`   | Mensaje del error                        |

### Contrato de trace para MATCH

Para `MATCH`:

- La expresión `MATCH` se evalúa exactamente una vez.
- Se registra su valor y tipo.
- Los `CASE` se evalúan secuencialmente.
- La evaluación termina en la primera coincidencia.
- Los `CASE` posteriores se representan como _short-circuited_.
- Si ningún `CASE` coincide, se selecciona `DEFAULT` cuando existe.
- Si no existe coincidencia ni `DEFAULT`, la regla produce `NO_ACTION`.
- `SET` y `EMIT` continúan siendo acciones y no nodos artificiales de trace.
- Los errores preservan el contrato de errores establecido anteriormente.

Este comportamiento está definido en [`docs/rfc/RFC-001-MATCH-CASE.md`](docs/rfc/RFC-001-MATCH-CASE.md).

---

## Short-Circuit

RuleForge modela explícitamente el comportamiento _short-circuit_. Esto forma parte del contrato del lenguaje, no es una optimización — el runtime garantiza que las ramas omitidas no se evalúan y que su omisión es observable en la traza.

Para `A AND B`, si `A` es falso, `B` no se evalúa.

La traza representa la rama omitida como:

```json
{
  "ShortCircuited": true,
  "Reason": "short_circuit"
}
```

El mismo principio se aplica a `AND`, `OR`, `ANY`, `ALL` y a la selección de ramas `MATCH`.

---

## Seguridad y Runtime Safety

RuleForge está diseñado deliberadamente como un lenguaje restringido. El lenguaje está pensado para entornos donde la predictibilidad importa más que la expresividad — evaluación de políticas, cumplimiento normativo, detección de fraude y cargas similares donde un resultado no determinista es un defecto, no una preocupación de rendimiento.

El modelo de ejecución proporciona:

- Ejecución acotada
- Tipado estricto
- Límites de seguridad del AST
- Semántica controlada de acciones
- Validación basada en _schema_
- Ausencia de efectos externos directos
- Evaluación determinista
- Códigos de error
- Trazabilidad

> El lenguaje **no** pretende ser Turing-complete.
> Es una decisión de diseño deliberada.
> La predictibilidad es tratada como un invariante del lenguaje y no solamente como una optimización.

---

## Desarrollo basado en contratos

RuleForge evoluciona mediante contratos y RFCs explícitos. Cada comportamiento no trivial se documenta antes de implementarse, y cada implementación rinde cuentas a su contrato mediante vectores de conformidad.

Contratos históricos: `CONTRACT_V8.md` a `CONTRACT_V11_4.md`.

**V12.0.0** incorpora:

```
docs/rfc/RFC-001-MATCH-CASE.md
```

El estado arquitectónico del release estable está documentado en:

```
docs/architecture/V12.0.0-BASELINE.md
```

---

## Arquitectura Cross-Language

RuleForge posee implementaciones independientes en Python y C# que trabajan sobre los mismos contratos del lenguaje.

El objetivo **no** es solamente compatibilidad de API. Las implementaciones deben coincidir en parsing, validación semántica, decisiones, errores, parches, trazas y comportamiento del compilador.

Por eso la conformidad _cross-language_ forma parte del **release gate** — no se libera un release si Python y C# difieren en cualquier comportamiento observable cubierto por los vectores de conformidad.

---

## Quality Gate V12.0.0

El release estable V12.0.0 fue validado mediante múltiples capas independientes. Cada capa es un gate separado; una falla en cualquiera bloquea el release.

| Validación                       | Resultado           |
|----------------------------------|---------------------|
| Python Core + Conformance        | 361 passed, 1 skipped |
| C# Core                          | 158/158             |
| C# API                           | 18/18               |
| Cross-language conformance       | 69/69 MATCH         |
| Compiler conformance             | 69/69 MATCH         |
| MATCH/CASE vectors               | 8/8                 |
| MATCH trace tests                | 6/6                 |
| Interpreter/Compiler parity      | 5/5                 |

Conformidad _cross-language_ y de compilador: **69 / 69 MATCH (100%)**.

Conformidad MATCH/CASE:

- 6 vectores válidos
- 2 vectores inválidos
- 8 / 8 validados

El release también conserva la suite de regresión de V11.

---

## Tooling

RuleForge proporciona una CLI para validación, evaluación y tracing.

**Evaluar:**

```bash
ruleforge eval rules.rf --context '{"customer":{"age":25}}'
```

**Validar:**

```bash
ruleforge check rules.rf --schema '{"customer":{"age":"Integer"}}'
```

**Trazar:**

```bash
ruleforge trace rules.rf --context '{"customer":{"age":25}}'
```

**Ayuda:**

```bash
ruleforge --help
```

---

## Instalación

Instalar desde PyPI (recomendado):

```bash
pip install ruleforge-engine
```

O clonar y desarrollar:

```bash
git clone https://github.com/eminem5410/ruleforge.git
cd ruleforge
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

El proyecto también contiene la implementación .NET y la infraestructura de conformidad.

---

## Estructura del proyecto

```text
ruleforge/
|
+-- ruleforge/
|   +-- lexer/
|   +-- parser/
|   +-- semantic/
|   +-- evaluator/
|   +-- compiler/
|   +-- api/
|   +-- engine.py
|
+-- dotnet/
|   +-- src/
|   |   +-- RuleForge.Core/
|   |   +-- RuleForge.Api/
|   |   +-- RuleForge.ConformanceRunner/
|   |
|   +-- tests/
|
+-- tests/
|   +-- conformance/
|   +-- property/
|   +-- test_evaluator.py
|   +-- test_engine.py
|   +-- test_trace.py
|   +-- test_sequential_semantics.py
|
+-- docs/
|   +-- rfc/
|   +-- architecture/
|
+-- CONTRACT_*.md
+-- README.md
+-- README.es.md
```

---

## Desarrollo y Quality Gates

RuleForge utiliza una estrategia de validación por capas. Cada capa habilita la siguiente — una regresión en cualquier nivel impide la progresión a la capa subsecuente.

```text
Python tests
      |
      v
C# Core tests
      |
      v
C# API tests
      |
      v
Cross-language conformance
      |
      v
Compiler conformance
      |
      v
Release gate
```

> Una funcionalidad del lenguaje **no se considera completa** hasta que su comportamiento es validado en las capas correspondientes.

---

## Reglas para la evolución del lenguaje

Los cambios futuros siguen estos principios:

| Principio                  | Descripción                                                                                          |
|----------------------------|------------------------------------------------------------------------------------------------------|
| **RFC First**              | Las funcionalidades importantes se especifican antes de implementarse.                              |
| **Por capas**              | Lexer → AST → Semantic → Evaluator → Trace.                                                         |
| **Paridad Cross-Language** | Python y C# deben coincidir en el comportamiento observable.                                        |
| **Aislamiento V11/V12**    | Las nuevas funcionalidades deben evitar cambios globales innecesarios sobre rutas de ejecución establecidas. |
| **Conformance como gate**  | Una funcionalidad no está completa hasta estar representada mediante vectores de conformidad y tests.   |

---

## Roadmap

### Completado

- **V11.0** — ANY / ALL
- **V11.1** — FILTER / MAP
- **V11.2** — Deep AST Trace
- **V11.3** — Trace Contract Hardening
- **V11.4** — Runtime Safety & Determinism
- **V11.5** — Compiler Performance & Sequential Runtime Semantics
- **V11.7** — AST Cache
- **V11.8** — Runtime y trace performance
- **V11.9** — CLI, REPL, tooling y desacoplamiento API
- **V12.0** — MATCH / CASE

### Consideraciones futuras

Posibles líneas de evolución incluyen:

- Integración con JSON Schema.
- Mayor expresividad del lenguaje.
- Pattern matching.
- Nuevas optimizaciones del runtime y compilador.

> Una construcción general de loops como `FOR EACH` permanece deliberadamente postergada porque requeriría revisar el modelo de ejecución acotado y **no Turing-complete** de RuleForge.

> Los elementos futuros son consideraciones de diseño, **no compromisos** de una versión específica.

---

## Configuración de desarrollo

Para regenerar los assets visuales y los READMEs desde el contenido baseline:

```bash
# 1. Crear el entorno local
python3 -m venv .venv
.venv/bin/pip install playwright
.venv/bin/playwright install chromium

# 2. Generar los assets PNG (logo, banner, diagrama de arquitectura, imagen OG)
.venv/bin/python build_ruleforge_assets.py

# 3. Regenerar README.md y README.es.md
.venv/bin/python rebuild_readmes.py
```

El directorio `.venv/` está gitignored. Cada contribuidor debe crear su propio entorno local después de clonar.

---

## Architectural Baseline

La arquitectura estable de V12.0.0 está congelada y documentada en:

```
docs/architecture/V12.0.0-BASELINE.md
```

El documento registra:

- Evolución V11.8 → V12.0
- Invariantes de RFC-001
- Integración arquitectónica
- Contrato de trace
- Resultados del Quality Gate
- Decisiones descartadas
- Consideraciones futuras
- Reglas para la evolución futura del lenguaje

---

## Release

**Release estable actual:** `v12.0.0`

---

<p align="center">
  <sub>RuleForge — Ejecución de reglas determinista para decisiones de política predecibles.</sub>
</p>
'''


def main() -> int:
    repo_root = Path.cwd()

    en_path = repo_root / "README.md"
    es_path = repo_root / "README.es.md"

    en_path.write_text(README_EN, encoding="utf-8")
    es_path.write_text(README_ES, encoding="utf-8")

    en_lines = README_EN.count("\n") + 1
    es_lines = README_ES.count("\n") + 1
    en_fences = README_EN.count("```")
    es_fences = README_ES.count("```")

    print("README.md       written: {} lines, {} code fences".format(en_lines, en_fences))
    print("README.es.md    written: {} lines, {} code fences".format(es_lines, es_fences))

    if en_fences % 2 != 0 or es_fences % 2 != 0:
        print("WARNING: unbalanced code fences detected.")
        return 1

    print("Done. Both README files rebuilt from baseline content.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
