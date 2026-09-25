import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from ruleforge.registry import Rule

@pytest.mark.asyncio
async def test_in_memory_lifecycle():
    from ruleforge.registry.in_memory_repository import InMemoryRuleRepository
    repo = InMemoryRuleRepository()
    
    v1 = await repo.save_rule("adult_check", 'RULE adult_check LANGUAGE 1 WHEN true THEN ALLOW END', 1)
    assert v1.status == "DRAFT"
    
    # No active rule yet -> should fail
    with pytest.raises(ValueError):
        await repo.get_rule("adult_check")
        
    activated = await repo.activate_rule("adult_check", 1)
    assert activated.status == "ACTIVE"
    
    fetched = await repo.get_rule("adult_check")
    assert fetched.version == 1
    
    v2 = await repo.save_rule("adult_check", 'RULE adult_check LANGUAGE 1 WHEN false THEN DENY "No" END', 1)
    await repo.activate_rule("adult_check", 2)
    fetched = await repo.get_rule("adult_check")
    assert fetched.version == 2
    assert fetched.status == "ACTIVE"
    
    # v1 should be archived now
    v1_fetched = await repo.get_rule("adult_check", version=1)
    assert v1_fetched.status == "ARCHIVED"
