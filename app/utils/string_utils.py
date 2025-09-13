from typing import Union
from uuid import UUID


def to_str(value: Union[str, UUID]) -> str:
    """Convert a value to string. If it's a UUID, convert it to its string representation."""
    if isinstance(value, UUID):
        return str(value)
    return value


def to_uuid(value: Union[str, UUID]) -> UUID:
    """Convert a value to UUID. If it's already a UUID, return it as is."""
    if isinstance(value, UUID):
        return value
    return UUID(value)
