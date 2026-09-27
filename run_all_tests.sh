#!/bin/bash
set -e # Fallar si cualquier comando falla

echo ">>> 1. CORRIENDO TESTS DE PYTHON (Core + Conformance)..."
pytest tests/ -q

echo ""
echo ">>> 2. COMPILANDO Y CORRIENDO TESTS DE C# (Core + API + Conformance)..."
cd dotnet
dotnet test
cd ..

echo ""
echo ">>> 3. CORRIENDO CROSS-LANGUAGE VALIDATION..."
python3 run_cross_language_conformance.py

echo ""
echo "✅ TODOS LOS TESTS PASARON EXITOSAMENTE (PYTHON, C#, CROSS-LANGUAGE)."
