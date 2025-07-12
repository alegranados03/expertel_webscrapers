from abc import ABC, abstractmethod
from typing import Any


class Annotation(ABC):
    @abstractmethod
    def get_annotation_name(self) -> str:
        raise NotImplementedError()  # pragma: no cover

    @abstractmethod
    def get_annotation_value(self) -> Any:
        raise NotImplementedError()  # pragma: no cover


class Count(Annotation):
    def __init__(self, field: str, alias: str | None = None):
        self.field = field
        self.alias = alias or f"{field}_count"

    def get_annotation_name(self) -> str:
        return self.alias

    def get_annotation_value(self) -> Any:
        return self.field 