# RuleForge

[English](./README.md) | [Español](./README.es.md)

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

```text
                         Rule Source
                              |
                              v
                       +--------------+
                       |    Lexer     |
                       +------+-------+
                              |
                              v
                       +--------------+
                       |    Parser    |
                       +------+-------+
                              |
                              v
                  +--------------------------+
                  |    Semantic Analyzer     |
                  |                          |
                  |        + Schema          |
                  +------------+-------------+
                               |
                               v
                       +---------------+
                       |   Evaluator   |
                       +-------+-------+
                               |
                +--------------+--------------+
                |              |              |
                v              v              v
            Decision         Trace        Patches
```

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

Instalación del paquete Python desde el repositorio:

```bash
pip install .
```

Para desarrollo:

```bash
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
