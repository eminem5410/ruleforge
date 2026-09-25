from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from .models import Rule
from ..persistence.models import RuleModel

class PostgresRuleRepository:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def save_rule(self, rule_id: str, source: str, language_version: int) -> Rule:
        async with self.session_factory() as session:
            stmt = select(func.max(RuleModel.version)).where(RuleModel.rule_id == rule_id)
            res = await session.execute(stmt)
            max_version = res.scalar() or 0
            
            new_version = max_version + 1
            now = datetime.now()
            
            rule_model = RuleModel(
                rule_id=rule_id, version=new_version, language_version=language_version,
                source=source, status="DRAFT", created_at=now, updated_at=now
            )
            session.add(rule_model)
            
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                raise ValueError("Concurrency conflict: Rule version already exists")
                
            return Rule(
                rule_id=rule_model.rule_id, version=rule_model.version,
                language_version=rule_model.language_version, source=rule_model.source,
                status=rule_model.status, created_at=rule_model.created_at, updated_at=rule_model.updated_at
            )

    async def get_rule(self, rule_id: str, version: Optional[int] = None) -> Rule:
        async with self.session_factory() as session:
            if version is not None:
                stmt = select(RuleModel).where(RuleModel.rule_id == rule_id, RuleModel.version == version)
            else:
                stmt = select(RuleModel).where(RuleModel.rule_id == rule_id, RuleModel.status == "ACTIVE")
                res = await session.execute(stmt)
                model = res.scalar_one_or_none()
                if not model:
                    stmt = select(RuleModel).where(RuleModel.rule_id == rule_id).order_by(RuleModel.version.desc()).limit(1)
                    res = await session.execute(stmt)
                    model = res.scalar_one_or_none()
                if not model:
                    raise ValueError(f"Rule '{rule_id}' not found")
                return self._to_domain(model)
            
            res = await session.execute(stmt)
            model = res.scalar_one_or_none()
            if not model:
                raise ValueError(f"Rule '{rule_id}' version {version} not found")
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
            # Buscar la última versión para archivarla
            stmt = select(RuleModel).where(RuleModel.rule_id == rule_id).order_by(RuleModel.version.desc()).limit(1)
            res = await session.execute(stmt)
            model = res.scalar_one_or_none()
            if not model:
                raise ValueError(f"Rule '{rule_id}' not found")
            model.status = "ARCHIVED"
            model.updated_at = datetime.now()
            await session.commit()

    def _to_domain(self, model: RuleModel) -> Rule:
        return Rule(
            rule_id=model.rule_id, version=model.version,
            language_version=model.language_version, source=model.source,
            status=model.status, created_at=model.created_at, updated_at=model.updated_at
        )
