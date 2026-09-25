from typing import Protocol, Any, runtime_checkable

@runtime_checkable
class RuleForgeAdapter(Protocol):
    @staticmethod
    def to_context(*args: Any, **kwargs: Any) -> dict:
        ...
