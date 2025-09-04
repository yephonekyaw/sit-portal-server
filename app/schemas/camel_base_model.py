import uuid
from datetime import datetime, date
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
        """Global serializer for all fields with comprehensive type handling"""

        # Handle UUID objects
        if isinstance(value, uuid.UUID):
            return str(value)

        # Handle Enum objects
        if isinstance(value, Enum):
            return value.value

        # Handle datetime objects (must come before date check)
        if isinstance(value, datetime):
            return value.isoformat()

        # Handle date objects
        if isinstance(value, date):
            return value.isoformat()

        # Handle lists and tuples recursively
        if isinstance(value, (list, tuple)):
            return [self.serialize_any(item) for item in value]

        # Handle dictionaries recursively
        if isinstance(value, dict):
            return {key: self.serialize_any(val) for key, val in value.items()}

        # Handle sets (convert to list)
        if isinstance(value, set):
            return [self.serialize_any(item) for item in value]

        # Handle bytes objects
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")

        # Handle other primitive types
        if isinstance(value, (str, int, float, bool)):
            return value

        # For any other object, try to convert to string as fallback
        try:
            return str(value)
        except Exception:
            return None
