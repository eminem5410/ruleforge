from pydantic import BaseModel
from typing import List, Literal
from datetime import datetime
import uuid

# SQLAlchemy Model
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, DateTime, JSON
from ..persistence.models import Base

class ApiKeyModel(Base):
    __tablename__ = "api_keys"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    key_hash: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="ACTIVE") # ACTIVE, REVOKED
    scopes: Mapped[List[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    last_used_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

# Domain Model
class ApiKey(BaseModel):
    id: str
    key_hash: str
    name: str
    status: str
    scopes: List[str]
    created_at: datetime
    last_used_at: datetime | None = None
    expires_at: datetime | None = None

class ApiKeyCreateResponse(BaseModel):
    id: str
    name: str
    scopes: List[str]
    plaintext_key: str  # Only returned once upon creation
