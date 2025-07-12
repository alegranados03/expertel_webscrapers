from abc import ABC, abstractmethod
from typing import Any, Generic, Optional, Type, TypeVar

from django.db.models import F, Model, OrderBy, Q, QuerySet as DjangoQuerySet

from shared.domain.entities.annotations import Annotation
from shared.domain.entities.pagination import QuerySet, QuerySetPagination
from shared.domain.entities.repositories import BaseRepository, ReadOnlyRepository, WriteOnlyRepository
from shared.domain.entities.specifications import Specification
from shared.infrastructure.django.buiders import DjangoORMAnnotationBuilder, DjangoORMSpecificationBuilder

T = TypeVar("T")
K = TypeVar("K", bound=Model)


class DjangoReadRepository(Generic[T, K], ReadOnlyRepository[T]):
    __model__: Type[K]

    @abstractmethod
    def to_entity(self, model: K) -> T:
        raise NotImplementedError()  # pragma: nocover

    def aggregate(self, pipeline: list[dict]) -> T:
        pass

    def get(self, criteria: list[Specification], annotations: list[Annotation] | None = None) -> T:
        specification_builder: DjangoORMSpecificationBuilder = DjangoORMSpecificationBuilder()
        annotation_builder: DjangoORMAnnotationBuilder = DjangoORMAnnotationBuilder()
        filters, _ = specification_builder.build(criteria)
        annotation_dict = annotation_builder.build(annotations) if annotations else {}

        try:
            queryset = self.__model__.objects.filter(**filters)
            if annotations:
                queryset = queryset.annotate(**annotation_dict)
            return self.to_entity(queryset.get())
        except self.__model__.DoesNotExist:
            raise Exception()

    def find(self, criteria: list[Specification], annotations: list[Annotation] | None = None) -> T | None:
        specification_builder: DjangoORMSpecificationBuilder = DjangoORMSpecificationBuilder()
        annotation_builder: DjangoORMAnnotationBuilder = DjangoORMAnnotationBuilder()
        filters, _ = specification_builder.build(criteria)
        annotation_dict = annotation_builder.build(annotations) if annotations else {}
        try:
            queryset = self.__model__.objects.filter(**filters)
            if annotations:
                queryset = queryset.annotate(**annotation_dict)
            return self.to_entity(queryset.get())
        except self.__model__.DoesNotExist:
            return None

    def filter(
        self,
        criteria: list[Specification],
        pagination: QuerySetPagination | None = None,
        order_by: list[str] | None = None,
        annotations: Optional[list[Annotation]] = None,
        distinct: bool = False,
    ) -> QuerySet[T]:
        specification_builder: DjangoORMSpecificationBuilder = DjangoORMSpecificationBuilder()
        annotation_builder: DjangoORMAnnotationBuilder = DjangoORMAnnotationBuilder()

        filters, exclusions = specification_builder.build(criteria)
        annotation_dict: dict = annotation_builder.build(annotations)

        # Manage special Q object for OR search
        search_q = filters.pop("_search_q", None)

        if search_q:
            # Apply the search Q object with other filters
            queryset: DjangoQuerySet = self.__model__.objects.filter(search_q, **filters).exclude(**exclusions)
        else:
            # normal behavior
            queryset: DjangoQuerySet = self.__model__.objects.filter(**filters).exclude(**exclusions)

        queryset = queryset.annotate(**annotation_dict)

        if distinct:
            queryset = queryset.distinct()

        if order_by:
            processed_order_by: list[OrderBy] = [
                F(field.lstrip("-")).desc(nulls_last=True) if field.startswith("-") else F(field).asc(nulls_last=True)
                for field in order_by
            ]
            queryset = queryset.order_by(*processed_order_by)

        entities: list[T] = (
            [self.to_entity(object) for object in queryset[pagination.array_slice]]
            if pagination
            else [self.to_entity(object) for object in queryset]
        )
        return QuerySet(data=entities, count=queryset.count())

    def all(self) -> QuerySet[T]:
        entities: list[T] = [self.to_entity(object) for object in self.__model__.objects.all()]
        return QuerySet(data=entities)

    def get_model_fields(self) -> list[str]:
        fields = self.__model__._meta.get_fields()
        names = [field.name for field in fields]
        return names


class DjangoWriteRepository(Generic[T, K], WriteOnlyRepository[T]):
    __model__: Type[K]

    @abstractmethod
    def to_orm_model(self, entity: T) -> K:
        raise NotImplementedError()  # pragma: nocover

    def update(self, entity: T) -> T:
        assert entity.id  # type: ignore[attr-defined]
        return self.save(entity)

    def save(self, entity: T) -> T:
        model: K = self.to_orm_model(entity)
        model.save()
        return self.to_entity(model)  # type: ignore[attr-defined]

    def delete(self, entity: T) -> None:
        model: K = self.to_orm_model(entity)
        model.delete()

    def bulk_create(self, entities: list[T]) -> list[T]:
        models: list[K] = [self.to_orm_model(entity) for entity in entities]
        return [
            self.to_entity(model) for model in self.__model__.objects.bulk_create(models)  # type: ignore[attr-defined]
        ]

    def bulk_update(self, entities: list[T], *, fields: list[str]) -> None:
        models: list[K] = [self.to_orm_model(entity) for entity in entities]
        self.__model__.objects.bulk_update(models, fields)

    def bulk_delete(self, entities: list[T]) -> None:
        self.__model__.objects.filter(id__in=[entity.id for entity in entities]).delete()  # type: ignore[attr-defined]


class DjangoFullRepository(DjangoReadRepository[T, K], DjangoWriteRepository[T, K], Generic[T, K]):
    __model__: Type[K]
