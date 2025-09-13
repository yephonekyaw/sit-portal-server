from sqlalchemy import TypeDecorator
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
import uuid


class StringUUID(TypeDecorator):
    """Custom type that stores UUIDs as strings in the database but handles UUID objects in Python."""

    impl = UNIQUEIDENTIFIER
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Convert Python value to database value."""
        if value is None:
            return value
        if isinstance(value, str):
            return uuid.UUID(value)
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))

    def process_result_value(self, value, dialect):
        """Convert database value to Python value (always string)."""
        if value is None:
            return value
        return str(value)
