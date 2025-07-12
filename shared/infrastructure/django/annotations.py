from typing import Any, Dict

from django.db.models import Count, F, Field, Func, IntegerField

from shared.domain.entities.annotations import Annotation


class JsonArrayLengthAnnotation(Annotation):
    def get_annotation(self) -> Dict[str, Any]:
        if self.output_field:
            return {self.alias: Func(F(self.field), function="jsonb_array_length", output_field=self.output_field)}
        return {self.alias: Func(F(self.field), function="jsonb_array_length")}


class RelatedItemsCountAnnotation(Annotation):
    def get_annotation(self) -> Dict[str, Any]:
        return {self.alias: Count(self.field, output_field=self.output_field or IntegerField())}
