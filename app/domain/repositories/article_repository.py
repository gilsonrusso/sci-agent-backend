from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID

from app.domain.entities.article import Article


class ArticleRepository(ABC):
    @abstractmethod
    def get_by_id(self, article_id: UUID) -> Optional[Article]:
        pass

    @abstractmethod
    def save(self, article: Article) -> None:
        pass

    @abstractmethod
    def get_all(self) -> List[Article]:
        pass
