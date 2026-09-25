import os
import ruleforge

def test_core_does_not_import_adapters():
    # La Golden Rule: El Core no debe saber nada de los dominios.
    # Escaneamos todos los archivos .py dentro del paquete 'ruleforge' 
    # y nos aseguramos de que no existan referencias a los adapters.
    ruleforge_path = os.path.dirname(ruleforge.__file__)
    forbidden_keywords = ["adapters", "fhir_adapter", "erp_adapter", "shipping_adapter", "FhirAdapter", "ErpAdapter", "ShippingAdapter"]
    
    violations = []
    for root, _, files in os.walk(ruleforge_path):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    for keyword in forbidden_keywords:
                        if keyword in content:
                            violations.append(f"File {file_path} contains forbidden keyword: {keyword}")
                            
    assert not violations, f"Architectural violation! Core depends on Adapters: {violations}"

from adapters.fhir_adapter import FhirAdapter
from adapters.erp_adapter import ErpAdapter
from adapters.shipping_adapter import ShippingAdapter
from adapters import RuleForgeAdapter

def test_adapters_comply_with_protocol():
    # Validamos en runtime que todos los adapters implementan el método to_context
    # con la firma esperada por el Protocol.
    assert isinstance(FhirAdapter, RuleForgeAdapter), "FhirAdapter does not comply with RuleForgeAdapter protocol"
    assert isinstance(ErpAdapter, RuleForgeAdapter), "ErpAdapter does not comply with RuleForgeAdapter protocol"
    assert isinstance(ShippingAdapter, RuleForgeAdapter), "ShippingAdapter does not comply with RuleForgeAdapter protocol"
