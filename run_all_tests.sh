#!/bin/bash
set -e # Fallar si cualquier comando falla

echo ">>> 1. CORRIENDO TESTS DE PYTHON (Core + Conformance)..."
pytest tests/ -q

echo ""
echo ">>> 2. COMPILANDO Y CORRIENDO TESTS DE C# (Core + API)..."
cd dotnet
dotnet test
cd ..

echo ""
echo ">>> 3. COMPILANDO CROSS-LANGUAGE RUNNER DE C#..."
dotnet build dotnet/src/RuleForge.ConformanceRunner/RuleForge.ConformanceRunner.csproj

echo ""
echo ">>> 4. CORRIENDO CROSS-LANGUAGE VALIDATION..."
python3 run_cross_language_conformance.py

echo ""
echo "✅ TODOS LOS TESTS PASARON EXITOSAMENTE (PYTHON, C#, CROSS-LANGUAGE)."
