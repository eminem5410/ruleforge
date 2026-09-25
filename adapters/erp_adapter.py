class ErpAdapter:
    @staticmethod
    def to_context(customer_entity: dict, invoice_entity: dict) -> dict:
        return {
            "customer": {
                "active": customer_entity.get("active", False),
                "credit_score": customer_entity.get("credit_score")
            },
            "invoice": {
                "total": float(invoice_entity.get("total", 0.0)),
                "status": invoice_entity.get("status", "UNKNOWN")
            }
        }
