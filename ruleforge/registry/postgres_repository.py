from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from .models import Rule
from ..persistence.models import RuleModel
from sqlalchemy.ext.asyncio import async_sessionmaker

class PostgresRuleRepository:
    def __init__(self, session_factory: async_sessionmaker):
        self.session_factory = session_factory

    async def save_rule(self, rule_id: str, source: str, language_version: int) -> Rule:
        async with self.session_factory() as session:
            stmt = select(func.max(RuleModel.version)).where(RuleModel.rule_id == rule_id)
            res = await session.execute(stmt)
            max_version = res.scalar() or 0
            new_version = max_version + 1
            now = datetime.now()
            rule_model = RuleModel(rule_id=rule_id, version=new_version, language_version=language_version, source=source, status="DRAFT", created_at=now, updated_at=now)
            session.add(rule_model)
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                raise ValueError("Concurrency conflict: Rule version already exists")
            return self._to_domain(rule_model)

    async def get_rule(self, rule_id: str, version: Optional[int] = None) -> Rule:
        async with self.session_factory() as session:
            if version is not None:
                stmt = select(RuleModel).where(RuleModel.rule_id == rule_id, RuleModel.version == version)
            else:
                stmt = select(RuleModel).where(RuleModel.rule_id == rule_id, RuleModel.status == "ACTIVE")
            
            res = await session.execute(stmt)
            model = res.scalar_one_or_none()
            if not model:
                raise ValueError(f"Rule '{rule_id}' not found")
            return self._to_domain(model)

    async def list_rules(self, status: Optional[str] = None) -> List[Rule]:
        async with self.session_factory() as session:
            stmt = select(RuleModel)
            if status:
                stmt = stmt.where(RuleModel.status == status)
            res = await session.execute(stmt)
            models = res.scalars().all()
            return [self._to_domain(m) for m in models]

    async def archive_rule(self, rule_id: str) -> None:
        async with self.session_factory() as session:
            stmt = select(RuleModel).where(RuleModel.rule_id == rule_id, RuleModel.status == "ACTIVE")
            res = await session.execute(stmt)
            model = res.scalar_one_or_none()
            if not model:
                raise ValueError(f"No ACTIVE rule found for '{rule_id}'")
            model.status = "ARCHIVED"
            model.updated_at = datetime.now()
            await session.commit()

    async def activate_rule(self, rule_id: str, version: int) -> Rule:
        async with self.session_factory() as session:
            stmt = select(RuleModel).where(RuleModel.rule_id == rule_id, RuleModel.status == "ACTIVE")
            res = await session.execute(stmt)
            active_model = res.scalar_one_or_none()
            if active_model:
                active_model.status = "ARCHIVED"
                active_model.updated_at = datetime.now()
            
            stmt = select(RuleModel).where(RuleModel.rule_id == rule_id, RuleModel.version == version)
            res = await session.execute(stmt)
            model = res.scalar_one_or_none()
            if not model:
                raise ValueError(f"Rule '{rule_id}' version {version} not found")
            model.status = "ACTIVE"
            model.updated_at = datetime.now()
            await session.commit()
            return self._to_domain(model)

    def _to_domain(self, model: RuleModel) -> Rule:
        return Rule(rule_id=model.rule_id, version=model.version, language_version=model.language_version, source=model.source, status=model.status, created_at=model.created_at, updated_at=model.updated_at)
