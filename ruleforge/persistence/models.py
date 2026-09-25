from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Text, DateTime, UniqueConstraint
from datetime import datetime

class Base(DeclarativeBase):
    pass

class RuleModel(Base):
    __tablename__ = "rules"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    rule_id: Mapped[str] = mapped_column(String, index=True)
    version: Mapped[int] = mapped_column(Integer)
    language_version: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)
    
    __table_args__ = (UniqueConstraint("rule_id", "version", name="uq_rule_version"),)
