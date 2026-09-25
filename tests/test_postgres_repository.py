import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from ruleforge.persistence.models import Base
from ruleforge.registry.postgres_repository import PostgresRuleRepository

DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def repo():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    repository = PostgresRuleRepository(session_factory)
    yield repository
    await engine.dispose()

@pytest.mark.asyncio
async def test_pg_lifecycle(repo):
    v1 = await repo.save_rule("promo", 'RULE promo LANGUAGE 1 WHEN true THEN ALLOW END', 1)
    assert v1.status == "DRAFT"
    
    await repo.activate_rule("promo", 1)
    active = await repo.get_rule("promo")
    assert active.version == 1
    assert active.status == "ACTIVE"
    
    v2 = await repo.save_rule("promo", 'RULE promo LANGUAGE 1 WHEN false THEN DENY "No" END', 1)
    await repo.activate_rule("promo", 2)
    active = await repo.get_rule("promo")
    assert active.version == 2
    
    v1_fetched = await repo.get_rule("promo", version=1)
    assert v1_fetched.status == "ARCHIVED"
