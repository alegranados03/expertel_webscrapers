from abc import ABC, abstractmethod
from typing import Generic, Optional, TypeVar

from pymongo.collection import Collection

from shared.domain.entities.annotations import Annotation
from shared.domain.entities.pagination import QuerySet, QuerySetPagination
from shared.domain.entities.specifications import Specification

T = TypeVar("T")


class ReadOnlyRepository(ABC, Generic[T]):
    @abstractmethod
    def get(self, criteria: list[Specification], annotations: list[Annotation] | None = None) -> T:
        raise NotImplementedError()  # pragma: no cover

    @abstractmethod
    def aggregate(self, pipeline: list[dict]) -> T:
        raise NotImplementedError()  # pragma: no cover

    @abstractmethod
    def find(
        self,
        criteria: list[Specification],
        annotations: list[Annotation] | None = None,
    ) -> T | None:
        raise NotImplementedError()  # pragma: no cover

    @abstractmethod
    def filter(
        self,
        criteria: list[Specification],
        pagination: QuerySetPagination | None = None,
        order_by: list[str] | None = None,
        annotations: list[Annotation] | None = None,
        distinct: bool = False,
    ) -> QuerySet[T]:
        raise NotImplementedError()  # pragma: no cover

    @abstractmethod
    def all(self) -> QuerySet[T]:
        raise NotImplementedError()  # pragma: no cover

    @abstractmethod
    def get_model_fields(self) -> list[str]:
        raise NotImplementedError()  # pragma: no cover


class WriteOnlyRepository(ABC, Generic[T]):
    @abstractmethod
    def save(self, entity: T) -> T:
        raise NotImplementedError()  # pragma: no cover

    @abstractmethod
    def update(self, entity: T) -> T:
        raise NotImplementedError()  # pragma: no cover

    @abstractmethod
    def delete(self, entity: T) -> None:
        raise NotImplementedError()  # pragma: no cover

    @abstractmethod
    def bulk_create(self, entities: list[T]) -> list[T]:
        raise NotImplementedError()  # pragma: no cover

    @abstractmethod
    def bulk_update(self, entities: list[T], *, fields: list[str]) -> None:
        raise NotImplementedError()  # pragma: no cover

    @abstractmethod
    def bulk_delete(self, entities: list[T]) -> None:
        raise NotImplementedError()  # pragma: no cover


class BaseRepository(ReadOnlyRepository[T], WriteOnlyRepository[T], Generic[T]):
    pass


class AbstractMongoDbCollectionRepository(ABC):

    def set_database(self, db_name: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def create_collection(
        self,
        collection_name: str,
        validator: Optional[dict[str, any]] = None,
        indexes: Optional[list[dict[str, any]]] = None,
    ) -> Collection:
        raise NotImplementedError

    @abstractmethod
    def drop_collection(self, collection_name: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_collections(self) -> list[str]:
        raise NotImplementedError
