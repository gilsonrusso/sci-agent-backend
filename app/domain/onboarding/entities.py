from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from uuid import UUID


@dataclass
class OnboardingTask:
    title: str
    description: str
    due_in_days: int = 7


@dataclass
class OnboardingProposta:
    topic: str
    title: str
    abstract: str
    roadmap: List[OnboardingTask] = field(default_factory=list)
    selected_articles: List[Dict[str, Any]] = field(default_factory=list)
    owner_id: Optional[UUID] = None

    def validate(self):
        if not self.topic:
            raise ValueError("O tópico da pesquisa é obrigatório.")
        if not self.title:
            raise ValueError("O título do projeto é obrigatório.")
        if not self.roadmap:
            raise ValueError("O roadmap inicial deve conter pelo menos uma tarefa.")
