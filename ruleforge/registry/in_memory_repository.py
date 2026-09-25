from typing import List, Optional
from datetime import datetime
from .models import Rule

class InMemoryRuleRepository:
    def __init__(self):
        self._store = {}  # {rule_id: {version: Rule}}

    def save_rule(self, rule_id: str, source: str, language_version: int) -> Rule:
        if rule_id not in self._store:
            self._store[rule_id] = {}
            
        versions = self._store[rule_id]
        new_version = max(versions.keys()) + 1 if versions else 1
        
        now = datetime.now()
        rule = Rule(
            rule_id=rule_id,
            version=new_version,
            language_version=language_version,
            source=source,
            status="DRAFT",
            created_at=now,
            updated_at=now
        )
        versions[new_version] = rule
        return rule

    def get_rule(self, rule_id: str, version: Optional[int] = None) -> Rule:
        if rule_id not in self._store:
            raise ValueError(f"Rule '{rule_id}' not found")
            
        versions = self._store[rule_id]
        if version is not None:
            if version not in versions:
                raise ValueError(f"Rule '{rule_id}' version {version} not found")
            return versions[version]
            
        # Return the latest version if no specific version is requested
        latest_version = max(versions.keys())
        return versions[latest_version]

    def list_rules(self, status: Optional[str] = None) -> List[Rule]:
        all_rules = []
        for versions in self._store.values():
            latest_version = max(versions.keys())
            rule = versions[latest_version]
            if status is None or rule.status == status:
                all_rules.append(rule)
        return all_rules

    def delete_rule(self, rule_id: str) -> None:
        if rule_id in self._store:
            del self._store[rule_id]
        else:
            raise ValueError(f"Rule '{rule_id}' not found")
