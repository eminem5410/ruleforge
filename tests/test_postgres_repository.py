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
async def test_pg_create_and_get(repo):
    rule = await repo.save_rule("adult_check", 'RULE adult_check LANGUAGE 1 WHEN true THEN ALLOW END', 1)
    assert rule.rule_id == "adult_check"
    assert rule.version == 1
    assert rule.status == "DRAFT"
    
    fetched = await repo.get_rule("adult_check")
    assert fetched.rule_id == "adult_check"

@pytest.mark.asyncio
async def test_pg_versioning_and_immutable_history(repo):
    v1 = await repo.save_rule("promo", 'RULE promo LANGUAGE 1 WHEN true THEN ALLOW END', 1)
    v2 = await repo.save_rule("promo", 'RULE promo LANGUAGE 1 WHEN false THEN DENY "No" END', 1)
    
    assert v1.version == 1
    assert v2.version == 2
    
    fetched_v1 = await repo.get_rule("promo", version=1)
    assert "ALLOW" in fetched_v1.source
    
    fetched_v2 = await repo.get_rule("promo", version=2)
    assert "DENY" in fetched_v2.source

@pytest.mark.asyncio
async def test_pg_archive_latest_rule(repo):
    rule = await repo.save_rule("r1", 'RULE r1 LANGUAGE 1 WHEN true THEN ALLOW END', 1)
    await repo.archive_rule("r1")
    
    archived = await repo.get_rule("r1", version=1)
    assert archived.status == "ARCHIVED"
