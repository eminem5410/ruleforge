from pydantic import BaseModel
from typing import Any, Dict

class EvaluateRequest(BaseModel):
    rules: str
    context: Dict[str, Any]
    schema: Dict[str, Dict[str, str]]
    explain: bool = False
