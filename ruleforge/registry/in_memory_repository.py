from typing import List, Optional
from datetime import datetime
from .models import Rule

class InMemoryRuleRepository:
    def __init__(self):
        self._store = {}

    async def save_rule(self, rule_id: str, source: str, language_version: int) -> Rule:
        if rule_id not in self._store:
            self._store[rule_id] = {}
            
        versions = self._store[rule_id]
        new_version = max(versions.keys()) + 1 if versions else 1
        
        now = datetime.now()
        rule = Rule(rule_id=rule_id, version=new_version, language_version=language_version, source=source, status="DRAFT", created_at=now, updated_at=now)
        versions[new_version] = rule
        return rule

    async def get_rule(self, rule_id: str, version: Optional[int] = None) -> Rule:
        if rule_id not in self._store:
            raise ValueError(f"Rule '{rule_id}' not found")
            
        versions = self._store[rule_id]
        if version is not None:
            if version not in versions:
                raise ValueError(f"Rule '{rule_id}' version {version} not found")
            return versions[version]
            
        active_rules = [r for r in versions.values() if r.status == "ACTIVE"]
        if active_rules:
            return active_rules[0]
        return versions[max(versions.keys())]

    async def list_rules(self, status: Optional[str] = None) -> List[Rule]:
        all_rules = []
        for versions in self._store.values():
            latest_version = max(versions.keys())
            rule = versions[latest_version]
            if status is None or rule.status == status:
                all_rules.append(rule)
        return all_rules

    async def archive_rule(self, rule_id: str) -> None:
        if rule_id not in self._store:
            raise ValueError(f"Rule '{rule_id}' not found")
        
        versions = self._store[rule_id]
        latest_version = max(versions.keys())
        versions[latest_version].status = "ARCHIVED"
        versions[latest_version].updated_at = datetime.now()
