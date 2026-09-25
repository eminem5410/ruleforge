from pydantic import BaseModel, field_validator
from typing import Any, Dict

ALLOWED_TYPES = {"Integer", "Decimal", "String", "Boolean", "Date"}

class EvaluateRequest(BaseModel):
    rules: str
    context: Dict[str, Any]
    context_schema: Dict[str, Dict[str, str]]
    explain: bool = False

    @field_validator("context_schema")
    @classmethod
    def validate_schema_types(cls, v):
        for obj_name, props in v.items():
            if not isinstance(props, dict):
                raise ValueError(f"Schema for '{obj_name}' must be a dictionary")
            for prop_name, prop_type in props.items():
                if prop_type not in ALLOWED_TYPES:
                    raise ValueError(f"Invalid type '{prop_type}' for {obj_name}.{prop_name}. Allowed: {ALLOWED_TYPES}")
        return v
