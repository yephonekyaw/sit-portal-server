import uuid
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, field_serializer
from pydantic.alias_generators import to_camel


class CamelCaseBaseModel(BaseModel):
    """
    Base model with camelCase field aliases and automatic serialization.

    This model automatically maps between camelCase (used in client requests/responses)
    and snake_case (used internally in Python):

    - Input: camelCase keys from the client are converted to snake_case for validation.
    - Internal: snake_case fields are used throughout the Python codebase.
    - Output: call `model_dump(by_alias=True)` to serialize fields back to camelCase
    for frontend responses.
    - Auto-serialization: UUIDs and Enums are automatically converted to strings.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    @field_serializer("*")
    def serialize_any(self, value):
        """Global serializer for all fields"""
        if isinstance(value, uuid.UUID):
            return str(value)
        elif isinstance(value, Enum):
            return value.value
        elif isinstance(value, datetime):
            return value.isoformat()
        return value
