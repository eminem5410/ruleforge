import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from ruleforge.registry import Rule

@pytest.mark.asyncio
async def test_in_memory_repository_create_and_get():
    from ruleforge.registry.in_memory_repository import InMemoryRuleRepository
    repo = InMemoryRuleRepository()
    
    rule = await repo.save_rule("adult_check", 'RULE adult_check LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END', 1)
    assert rule.rule_id == "adult_check"
    assert rule.version == 1
    assert rule.status == "DRAFT"
    
    fetched = await repo.get_rule("adult_check")
    assert fetched.rule_id == "adult_check"
    assert fetched.version == 1

@pytest.mark.asyncio
async def test_in_memory_repository_versioning():
    from ruleforge.registry.in_memory_repository import InMemoryRuleRepository
    repo = InMemoryRuleRepository()
    
    v1 = await repo.save_rule("promo", 'RULE promo LANGUAGE 1 WHEN true THEN ALLOW END', 1)
    v2 = await repo.save_rule("promo", 'RULE promo LANGUAGE 1 WHEN false THEN DENY "No" END', 1)
    
    assert v1.version == 1
    assert v2.version == 2
    
    fetched_v1 = await repo.get_rule("promo", version=1)
    fetched_v2 = await repo.get_rule("promo", version=2)
    
    assert fetched_v1.source != fetched_v2.source

@pytest.mark.asyncio
async def test_in_memory_repository_list_and_archive():
    from ruleforge.registry.in_memory_repository import InMemoryRuleRepository
    repo = InMemoryRuleRepository()
    await repo.save_rule("r1", 'RULE r1 LANGUAGE 1 WHEN true THEN ALLOW END', 1)
    await repo.save_rule("r2", 'RULE r2 LANGUAGE 1 WHEN true THEN ALLOW END', 1)
    
    rules = await repo.list_rules()
    assert len(rules) == 2
    
    await repo.archive_rule("r1")
    rules = await repo.list_rules()
    assert len(rules) == 2  # Still there, but archived
    
    archived_rule = await repo.get_rule("r1")
    assert archived_rule.status == "ARCHIVED"
