from abc import ABC, abstractmethod
from typing import Any


class Specification(ABC):
    @abstractmethod
    def get_field_name(self) -> str:
        raise NotImplementedError()  # pragma: no cover

    @abstractmethod
    def get_field_value(self) -> Any:
        raise NotImplementedError()  # pragma: no cover

    @abstractmethod
    def is_satisfied_by(self, obj: Any) -> bool:
        raise NotImplementedError()  # pragma: no cover


class FieldSpecification(Specification):
    def __init__(self, field: str, value: Any):
        self.field = field
        self.value = value

    def get_field_name(self) -> str:
        return self.field

    def get_field_value(self) -> Any:
        return self.value

    def is_satisfied_by(self, obj: Any) -> bool:
        return getattr(obj, self.field, None) == self.value
