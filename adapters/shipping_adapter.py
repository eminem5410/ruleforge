from decimal import Decimal

class ShippingAdapter:
    @staticmethod
    def to_context(shipment_entity: dict) -> dict:
        weight = shipment_entity.get("weight")
        if weight is not None:
            weight = Decimal(str(weight))
            
        return {
            "shipment": {
                "weight": weight,
                "zone": shipment_entity.get("destination_zone"),
                "priority": shipment_entity.get("is_priority")
            }
        }
