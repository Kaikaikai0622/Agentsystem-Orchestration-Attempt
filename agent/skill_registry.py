"""
Skill registry for explicit skill definitions.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type


@dataclass
class SkillDefinition:
    name: str
    cls: Type[Any]
    keywords: List[str] = field(default_factory=list)


SKILL_REGISTRY: Dict[str, SkillDefinition] = {}


def register_skill(name: str, keywords: Optional[List[str]] = None):
    def decorator(cls: Type[Any]) -> Type[Any]:
        SKILL_REGISTRY[name] = SkillDefinition(name=name, cls=cls, keywords=keywords or [])
        return cls
    return decorator


def get_skill_definition(name: str) -> Optional[SkillDefinition]:
    return SKILL_REGISTRY.get(name)
