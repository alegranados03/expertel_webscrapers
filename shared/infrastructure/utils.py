import math
import os
import re
import unicodedata
from collections import defaultdict
from enum import Enum
from typing import Type
from urllib import parse

from shared.domain.entities.pagination import PaginatedQuerySet, PaginationData, QuerySet
from shared.domain.enums import DataUnit


def unicode_transformed_string(name: str) -> str:
    """
    Converts a name to uppercase, removes accents and special characters,
    and replaces spaces with underscores.

    Args:
        name (str): The original name.

    Returns:
        str: The transformed name.
    """
    normalized_name = unicodedata.normalize("NFD", name).strip()
    name_without_accents = "".join(c for c in normalized_name if unicodedata.category(c) != "Mn")
    cleaned_name = re.sub(r"[^\w\s]", "", name_without_accents)
    formatted_name = re.sub(r"\s+", "_", cleaned_name)
    return formatted_name.lower()


def get_previous_month_year(month: int, year: int):
    if month == 1:
        return 12, year - 1
    return month - 1, year


def paginate_queryset(*, queryset: QuerySet, page: int, page_size: int, url: str) -> dict:
    def _replace_query_param(url: str, query_param: str, query_value: str) -> str:
        parsed_url = parse.urlparse(url)
        query_params = parse.parse_qs(parsed_url.query)
        query_params[query_param] = [query_value]
        new_query = parse.urlencode(query_params, doseq=True)
        return parse.urlunparse(parsed_url._replace(query=new_query))

    total_pages: int = math.ceil(queryset.count / page_size)
    return PaginatedQuerySet(
        pagination_data=PaginationData(
            previousPage=_replace_query_param(url, "page", str(page - 1)) if page - 1 > 0 else None,
            nextPage=_replace_query_param(url, "page", str(page + 1)) if page + 1 <= total_pages else None,
            currentPage=page,
            totalPages=total_pages,
            totalItemsOnPage=min(len(queryset.data), page_size),
            totalItems=queryset.count,
            pageSize=page_size,
        ),
        results=queryset.data,
    ).model_dump()


def find_enum_value_duplicates(*enums: Type[Enum]) -> dict[str, list[str]]:
    """
    Detects duplicate values between multiple Enums.

    Returns a dictionary with the duplicate value as the key,
    and a list of the enum names where it appears as the value.
    """
    value_map = defaultdict(list)

    for enum_class in enums:
        for member in enum_class:
            value_map[member.value].append(enum_class.__name__)

    duplicates = {value: sources for value, sources in value_map.items() if len(sources) > 1}
    return duplicates


def to_bytes(value: float, unit: DataUnit) -> int:
    """
    Converts a value to bytes based on the given unit.

    :param value: Numeric value to convert.
    :param unit: Unit ('KB', 'MB', 'GB', 'TB').
    :return: Value in bytes.
    """
    unit = unit.upper()
    units = {
        DataUnit.KB: 1024,
        DataUnit.MB: 1024**2,
        DataUnit.GB: 1024**3,
        DataUnit.TB: 1024**4,
    }

    if unit not in units:
        raise ValueError(f"Invalid unit: {unit}. Use one of: {', '.join(units.keys())}")

    return int(value * units[unit])


def from_bytes(value: float, unit: DataUnit) -> float:
    """
    Converts a byte value to the specified unit.

    :param value: Value in bytes.
    :param unit: Target unit ('KB', 'MB', 'GB', 'TB').
    :return: Value converted to the specified unit.
    """
    unit = unit.upper()
    units = {
        DataUnit.KB: 1024,
        DataUnit.MB: 1024**2,
        DataUnit.GB: 1024**3,
        DataUnit.TB: 1024**4,
    }

    if unit not in units:
        raise ValueError(f"Invalid unit: {unit}. Use one of: {', '.join(units.keys())}")

    return value / units[unit]


def extract_numbers_from_text(text: str) -> str:
    if text is None:
        return "0"
    numbers = re.sub(r"[^\d]", "", text)
    return numbers


def get_file_extension(file) -> str | None:
    content_type = file.content_type
    if content_type == "text/csv":
        return "csv"
    elif content_type in [
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ]:
        return "xslx"
    else:
        return None


def transform_phone_number(cad: str):
    new_cad = re.sub(r"\D", "", cad)
    match = re.search(r"\d+", new_cad)

    if match:
        num = match.group(0)
        if 10 <= len(num) <= 11:
            if len(num) == 11:
                num = num[1:]
            return int(num)
    return cad
