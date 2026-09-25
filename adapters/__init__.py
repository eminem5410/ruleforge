from typing import Protocol, Any

class RuleForgeAdapter(Protocol):
    @staticmethod
    def to_context(*args: Any, **kwargs: Any) -> dict:
        ...
