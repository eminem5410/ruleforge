
RuleForge
English | Español

Estado: Estable
Tests Python
Tests C#
Conformidad Cross-Language

RuleForge es un motor de reglas determinista, fuertemente tipado y aislado (sandboxed). Evalúa reglas de negocio sin ambigüedades, asegurando que las implementaciones en Python y C# produzcan resultados idénticos.

¿Por qué RuleForge?
Determinista y Acotado: Sin bucles, sin recursión, sin efectos secundarios. Se garantiza que toda evaluación de reglas termine dentro de límites estrictos de ejecución.
Fuertemente Tipado: El análisis semántico rechaza inconsistencias de tipos en tiempo de compilación (ej. comparar un Integer con un String).
Cross-Language: Escribe las reglas una vez; ejecútalas en Python o .NET/C# con decisiones y trazas idénticas al 100%.
Paridad de Compilador: El Intérprete y el Compilador demuestran ser matemáticamente equivalentes mediante 69/69 vectores de conformidad.
Ejemplo del Lenguaje (V12.0.0)
RULE customer_status LANGUAGE 1
MATCH customer.status
CASE "ACTIVE":
    ALLOW
CASE "BLOCKED":
    DENY "Acceso bloqueado"
DEFAULT:
    NO_ACTION
END
Herramientas (CLI y REPL)
RuleForge provee una CLI nativa para validar, evaluar y trazar reglas.

Evaluar
ruleforge eval rules.rf --context '{"customer":{"age":25}}'
Validar (Check)
ruleforge check rules.rf --schema '{"customer":{"age":"Integer"}}'
Trazar
ruleforge trace rules.rf --context '{"customer":{"age":25}}'
Arquitectura y Documentación
Baseline Arquitectónico V12.0.0
RFC-001: MATCH / CASE
Instalación
pip install .
Resultados del Quality Gate (V12.0.0)
Python Core + Conformance: 361 pasaron, 1 omitido
C# Core: 158/158 pasaron
C# API: 18/18 pasaron
Conformidad Cross-Language: 69/69 MATCH (100%)
Conformidad de Compilador: 69/69 MATCH (100%)
