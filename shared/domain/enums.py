from enum import Enum, IntEnum


class DataUnit(str, Enum):
    B = "B"
    KB = "KB"
    MB = "MB"
    GB = "GB"
    TB = "TB"


class CriteriaOperator(IntEnum):
    EQUAL: int = 0
    IN: int = 1
    LTE: int = 2
    GTE: int = 3
    ICONTAINS: int = 4
    EXACT: int = 5
    RANGE: int = 6
    IEXACT: int = 7
    STARTSWITH: int = 8
    ISTARTSWITH: int = 9
    NOT_IN: int = 10
    IS_NULL: int = 11
