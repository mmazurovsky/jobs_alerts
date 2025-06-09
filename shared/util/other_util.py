
from enum import Enum
from pydantic_core import core_schema
from pydantic import GetCoreSchemaHandler


def enable_enum_name_deserialization(enum_cls: type[Enum]):
    def _validate(input_str: str) -> Enum:
        try:
            return enum_cls[input_str]
        except KeyError:
            raise ValueError(f"Input should be one of: {', '.join(e.name for e in enum_cls)}")

    def __get_pydantic_core_schema__(cls, source_type, handler: GetCoreSchemaHandler):
        return core_schema.no_info_plain_validator_function(_validate)

    enum_cls.__get_pydantic_core_schema__ = classmethod(__get_pydantic_core_schema__)
    return enum_cls