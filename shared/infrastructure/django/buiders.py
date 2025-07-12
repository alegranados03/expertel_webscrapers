from typing import Any

from django.db.models import Count, Q

from shared.domain.entities.annotations import Annotation
from shared.domain.entities.specifications import Specification


class DjangoORMSpecificationBuilder:
    def build(self, criteria: list[Specification]) -> tuple[dict, dict]:
        filters = {}
        exclusions = {}
        
        for spec in criteria or []:
            field_name = spec.get_field_name()
            field_value = spec.get_field_value()
            
            if field_name.startswith("!"):
                # Exclusion
                exclusions[field_name[1:]] = field_value
            else:
                filters[field_name] = field_value
        
        return filters, exclusions


class DjangoORMAnnotationBuilder:
    def build(self, annotations: list[Annotation] | None) -> dict[str, Any]:
        if not annotations:
            return {}
        
        annotation_dict = {}
        for annotation in annotations:
            annotation_name = annotation.get_annotation_name()
            annotation_value = annotation.get_annotation_value()
            
            # Simple implementation for Count annotation
            if hasattr(annotation, 'field'):
                annotation_dict[annotation_name] = Count(annotation.field)
            else:
                annotation_dict[annotation_name] = annotation_value
        
        return annotation_dict
