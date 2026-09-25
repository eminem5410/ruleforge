import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from decimal import Decimal
from ruleforge import RuleForgeEngine
from adapters.shipping_adapter import ShippingAdapter

# Schema definido exclusivamente para este dominio de logística ficticio
SHIPPING_SCHEMA = {
    "shipment": {"weight": "Decimal", "zone": "String", "priority": "Boolean"}
}
engine = RuleForgeEngine(SHIPPING_SCHEMA)

def test_custom_adapter_shipping_express_rule():
    # Entidad de dominio: Un paquete de logística
    shipment = {
        "tracking_id": "XYZ123",
        "weight": "15.5",        # String en el origen
        "destination_zone": "C",
        "is_priority": True
    }
    
    # El adapter traduce el dominio de logística al contexto genérico
    context = ShippingAdapter.to_context(shipment)
    
    # Verificamos la precisión Decimal exacta
    assert context["shipment"]["weight"] == Decimal("15.5")
    
    # RuleForge evalúa la regla de negocio sin saber qué es un "shipment"
    rule = '''
    RULE priority_zone_c LANGUAGE 1
    WHEN shipment.zone == "C" AND shipment.weight > 10.0 AND shipment.priority == true
    THEN APPLY "EXPRESS_SHIPPING"
    ELSE ALLOW
    END
    '''
    decisions = engine.evaluate(rule, context)
    
    assert decisions[0].matched == True
    assert decisions[0].actions[0].action_type == "APPLY"
    assert decisions[0].actions[0].value == "EXPRESS_SHIPPING"

def test_custom_adapter_missing_data_is_null():
    # Faltan datos en el dominio
    shipment = {"tracking_id": "ABC987", "destination_zone": "A"} # Falta peso y prioridad
    
    context = ShippingAdapter.to_context(shipment)
    
    # Los datos ausentes se mapean a NULL, respetando el contrato
    assert context["shipment"]["weight"] is None
    assert context["shipment"]["priority"] is None
    
    rule = 'RULE r LANGUAGE 1 WHEN shipment.priority IS NULL THEN ALLOW END'
    decisions = engine.evaluate(rule, context)
    assert decisions[0].matched == True
