from typing import Any

from shared.domain.entities.specifications import SpecificationParser


class EqualsSpecification(SpecificationParser):
    def __init__(self, field: str, value: Any) -> None:
        super().__init__(field, value)

    def get_field(self) -> str:
        return self.field


class InSpecification(SpecificationParser):
    def __init__(self, field: str, value: Any) -> None:
        super().__init__(field, value)

    def get_field(self) -> str:
        return f"{self.field}__in"


class LteSpecification(SpecificationParser):
    def __init__(self, field: str, value: Any) -> None:
        super().__init__(field, value)

    def get_field(self) -> str:
        return f"{self.field}__lte"


class GteSpecification(SpecificationParser):
    def __init__(self, field: str, value: Any) -> None:
        super().__init__(field, value)

    def get_field(self) -> str:
        return f"{self.field}__gte"


class ExactSpecification(SpecificationParser):
    def __init__(self, field: str, value: Any) -> None:
        super().__init__(field, value)

    def get_field(self) -> str:
        return f"{self.field}__exact"


class IcontainsSpecification(SpecificationParser):
    def __init__(self, field: str, value: Any) -> None:
        super().__init__(field, value)

    def get_field(self) -> str:
        return f"{self.field}__icontains"


class RangeSpecification(SpecificationParser):
    def __init__(self, field: str, value: Any) -> None:
        super().__init__(field, value)

    def get_field(self) -> str:
        return f"{self.field}__range"


class IsNullSpecification(SpecificationParser):
    def __init__(self, field: str, value: bool) -> None:
        super().__init__(field, value)

    def get_field(self) -> str:
        return f"{self.field}__isnull"
