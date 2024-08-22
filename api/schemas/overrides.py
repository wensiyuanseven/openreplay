# 该代码片段实现了一些用于数据模型和枚举处理的工具和基类。具体来说，它通过 Pydantic 和 Python 枚举类提供了一个基础模型类 BaseModel，可以自动将属性名从蛇形命名法（snake_case）转换为驼峰命名法（camelCase），并通过自定义配置对模型的 JSON Schema 进行额外处理。
# 同时，代码还定义了一个扩展的枚举类 Enum，提供了检查枚举值是否存在的方法。最后，ORUnion 类允许根据类型和区分符动态创建一个联合类型的校验器。
from typing import TypeVar, Annotated, Union
from enum import Enum as _Enum
from pydantic import BaseModel as _BaseModel
from pydantic import ConfigDict, TypeAdapter, Field
from pydantic.types import AnyType


# 将属性名从蛇形命名法转换为驼峰命名法
# 参数：
# - snake_str: 字符串类型，蛇形命名的字符串
# 返回值：
# - 转换后的驼峰命名字符串
def attribute_to_camel_case(snake_str: str) -> str:
    components = snake_str.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


# 在生成 JSON Schema 时移除被标记为 "doc_hidden" 的属性
# 参数：
# - schema: 字典类型，包含 Pydantic 模型的 JSON Schema
# - _: 未使用的参数，用于保持函数签名一致
def schema_extra(schema: dict, _):
    props = {}
    for k, v in schema.get("properties", {}).items():
        if not v.get("doc_hidden", False):
            props[k] = v
    schema["properties"] = props


# 自定义的 Pydantic 基类模型
# 该类自动将属性名从蛇形命名法转换为驼峰命名法，并在生成 JSON Schema 时移除标记为 "doc_hidden" 的属性
class BaseModel(_BaseModel):
    model_config = ConfigDict(alias_generator=attribute_to_camel_case, use_enum_values=True, json_schema_extra=schema_extra)


# 扩展的枚举类，添加了检查值是否存在的方法
class Enum(_Enum):
    # 检查枚举类是否包含某个值
    # 参数：
    # - value: 任意类型，要检查的值
    # 返回值：
    # - 布尔值，True 表示枚举类包含该值，False 表示不包含
    @classmethod
    def has_value(cls, value) -> bool:
        return value in cls._value2member_map_


# 泛型类型变量
T = TypeVar("T")


# 动态创建联合类型校验器的类
class ORUnion:
    # 创建一个新的联合类型校验器
    # 参数：
    # - union_types: 联合类型，使用 AnyType 表示
    # - discriminator: 字符串类型，区分符，用于选择联合类型中的具体类型
    # 返回值：
    # - 返回一个使用 TypeAdapter 创建的联合类型校验器
    def __new__(self, union_types: Union[AnyType], discriminator: str) -> T:
        return lambda **args: TypeAdapter(Annotated[union_types, Field(discriminator=discriminator)]).validate_python(args)
