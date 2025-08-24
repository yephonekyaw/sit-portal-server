from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelCaseBaseModel(BaseModel):
    """
    Base model with camelCase field aliases.

    This model automatically maps between camelCase (used in client requests/responses)
    and snake_case (used internally in Python):

    - Input: camelCase keys from the client are converted to snake_case for validation.
    - Internal: snake_case fields are used throughout the Python codebase.
    - Output: call `model_dump(by_alias=True)` to serialize fields back to camelCase
    for frontend responses.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
