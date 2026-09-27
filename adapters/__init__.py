from typing import Protocol, Any, runtime_checkable

@runtime_checkable
class RuleForgeAdapter(Protocol):
    @staticmethod
    def to_context(*args: Any, **kwargs: Any) -> dict:
        ...

from .fhir_adapter import FhirAdapter
from .erp_adapter import ErpAdapter
from .shipping_adapter import ShippingAdapter
