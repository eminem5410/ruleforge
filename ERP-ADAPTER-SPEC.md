# RuleForge ERP Adapter Specification

Defines how ERP entities (used in ContaFlow) map to RuleForge Context.
The RuleForge Core only sees the "RuleForge Context" section. It knows nothing about ContaFlow, ERP, or business logic.

## 1. Supported Entities (V2.2.0)
- Customer
- Invoice
- Product
- Sale
- Payment
- Stock

## 2. Context Mapping Schema & Rules
The ErpAdapter must output a RuleForge Context matching this schema.
Missing fields in ERP entities MUST be mapped to `None` (NULL). Numeric values (totals, prices, amounts) MUST be converted to `Decimal` to preserve exact precision.

{
  "customer": { "active": "Boolean", "credit_score": "Integer" },
  "invoice": { "total": "Decimal", "status": "String" },
  "product": { "price": "Decimal", "category": "String" },
  "sale": { "total": "Decimal", "status": "String" },
  "payment": { "amount": "Decimal", "method": "String" },
  "stock": { "quantity": "Integer", "warehouse": "String" }
}

## 3. Detailed Mappings

### Customer
ERP Input: Customer(active=True, credit_score=750)
RuleForge Context: { "customer": { "active": true, "credit_score": 750 } }

### Invoice
ERP Input: Invoice(total=150000.50, status="PENDING")
RuleForge Context: { "invoice": { "total": Decimal("150000.50"), "status": "PENDING" } }

### Product (NEW)
ERP Input: Product(price=45000.00, category="ELECTRONICS")
RuleForge Context: { "product": { "price": Decimal("45000.00"), "category": "ELECTRONICS" } }

### Sale (NEW)
ERP Input: Sale(total=150000.50, status="COMPLETED")
RuleForge Context: { "sale": { "total": Decimal("150000.50"), "status": "COMPLETED" } }

### Payment (NEW)
ERP Input: Payment(amount=150000.50, method="TRANSFER")
RuleForge Context: { "payment": { "amount": Decimal("150000.50"), "method": "TRANSFER" } }

### Stock (NEW)
ERP Input: Stock(quantity=12, warehouse="WH-A")
RuleForge Context: { "stock": { "quantity": 12, "warehouse": "WH-A" } }
