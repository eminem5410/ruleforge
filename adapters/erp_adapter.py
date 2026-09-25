from decimal import Decimal

class ErpAdapter:
    @staticmethod
    def to_context(customer_entity: dict, invoice_entity: dict) -> dict:
        # Si los campos no existen, dejamos que el Engine lo tome como NULL (missing property)
        # en lugar de inventar un default.
        
        total = invoice_entity.get("total")
        if total is not None:
            total = Decimal(str(total)) # Preservar precisión exacta
            
        return {
            "customer": {
                "active": customer_entity.get("active"),
                "credit_score": customer_entity.get("credit_score")
            },
            "invoice": {
                "total": total,
                "status": invoice_entity.get("status")
            }
        }
