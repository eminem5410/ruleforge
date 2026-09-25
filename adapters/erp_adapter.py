from decimal import Decimal
from typing import Optional, Dict, Any

class ErpAdapter:
    @staticmethod
    def to_context(
        customer_entity: Dict[str, Any], 
        invoice_entity: Dict[str, Any],
        product_entity: Optional[Dict[str, Any]] = None,
        sale_entity: Optional[Dict[str, Any]] = None,
        payment_entity: Optional[Dict[str, Any]] = None,
        stock_entity: Optional[Dict[str, Any]] = None
    ) -> dict:
        
        def _get_decimal(data: dict, key: str):
            """Helper para extraer y convertir a Decimal de forma segura."""
            val = data.get(key)
            if val is not None:
                return Decimal(str(val))
            return None

        # 1 y 2: Customer e Invoice (Siempre requeridos)
        context = {
            "customer": {
                "active": customer_entity.get("active"),
                "credit_score": customer_entity.get("credit_score")
            },
            "invoice": {
                "total": _get_decimal(invoice_entity, "total"),
                "status": invoice_entity.get("status")
            }
        }
        
        # 3. Product (Opcional)
        if product_entity is not None:
            context["product"] = {
                "price": _get_decimal(product_entity, "price"),
                "category": product_entity.get("category")
            }
            
        # 4. Sale (Opcional)
        if sale_entity is not None:
            context["sale"] = {
                "total": _get_decimal(sale_entity, "total"),
                "status": sale_entity.get("status")
            }
            
        # 5. Payment (Opcional)
        if payment_entity is not None:
            context["payment"] = {
                "amount": _get_decimal(payment_entity, "amount"),
                "method": payment_entity.get("method")
            }
            
        # 6. Stock (Opcional)
        if stock_entity is not None:
            context["stock"] = {
                "quantity": stock_entity.get("quantity"),
                "warehouse": stock_entity.get("warehouse")
            }
            
        return context
