from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from pydantic import BaseModel

from django.db.models import Field


class Annotation(BaseModel, ABC):
    field: str
    alias: str
    output_field: Optional[Field] = None

    class Config:
        arbitrary_types_allowed = True

    @abstractmethod
    def get_annotation(self) -> Dict[str, Any]:
        raise NotImplementedError()
