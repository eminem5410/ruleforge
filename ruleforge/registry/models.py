from pydantic import BaseModel
from typing import Literal
from datetime import datetime

class Rule(BaseModel):
    rule_id: str
    version: int
    language_version: int
    source: str
    status: Literal["DRAFT", "ACTIVE", "ARCHIVED"]
    created_at: datetime
    updated_at: datetime
