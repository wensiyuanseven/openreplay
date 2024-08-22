# 这些工具函数和装饰器通常在数据预处理和验证阶段使用，帮助开发者确保数据格式的一致性，并简化一些常见的数据转换操作。例如，transform_email可以确保用户输入的电子邮件格式统一，remove_whitespace则可以清理多余的空格，以确保字符串比较的准确性。通过这些工具函数，开发者能够更轻松地编写可靠、可维护的代码。

from .overrides import Enum

from typing import Union, Any, Type

NAME_PATTERN = r"^[a-z,A-Z,0-9,\-,é,è,à,ç, ,|,&,\/,\\,_,.,#]*$"


# 描述: 将输入的电子邮件地址转换为小写并去除首尾空格。
# 参数:
# email: 字符串类型的电子邮件地址。
# 返回值: 处理后的电子邮件地址，如果输入不是字符串则原样返回。
def transform_email(email: str) -> str:
    return email.lower().strip() if isinstance(email, str) else email


# 描述: 将整数转换为字符串。
# 参数:
# value: 整数类型的值。
# 返回值: 转换后的字符串形式的值，如果输入不是整数则原样返回。
def int_to_string(value: int) -> str:
    return str(value) if isinstance(value, int) else value


# 描述: 去除字符串中的多余空格，只保留单个空格分隔的单词。
# 参数:
# value: 字符串类型的值。
# 返回值: 去除多余空格后的字符串，如果输入不是字符串则原样返回。
def remove_whitespace(value: str) -> str:
    return " ".join(value.split()) if isinstance(value, str) else value


# 描述: 移除列表中的重复值。
# 参数:
# value: 列表类型的值。
# 返回值: 去重后的列表。如果列表中元素为整数或字典，保留原列表。如果输入不是列表或为空，则原样返回。
def remove_duplicate_values(value: list) -> list:
    if value is not None and isinstance(value, list):
        if len(value) > 0 and (isinstance(value[0], int) or isinstance(value[0], dict)):
            return value
        value = list(set(value))
    return value


# 描述: 将单个非列表的值转换为包含该值的列表。
# 参数:
# value: 任意类型的值或列表。
# 返回值: 如果输入是非列表的单个值，则返回一个包含该值的列表；如果输入本来就是列表，则原样返回。
def single_to_list(value: Union[list, Any]) -> list:
    if value is not None and not isinstance(value, list):
        value = [value]
    return value


# 描述: 返回一个函数，该函数用于检查列表中的每个字典是否具有指定枚举类型的值，并添加isEvent标志。

# 参数:


# events_enum: 包含枚举类型的列表。
# 返回值: 一个函数，该函数接收一个列表作为输入，并在每个元素中添加isEvent标志，指示其类型是否在指定的枚举类型中。
def force_is_event(events_enum: list[Type[Enum]]):
    # 内部函数 fn:
    # 描述: 检查列表中的每个元素是否属于指定的枚举类型，并添加isEvent属性。
    # 参数:
    # value: 列表类型的值。
    # 返回值: 添加了isEvent属性的列表。
    def fn(value: list):
        if value is not None and isinstance(value, list):
            for v in value:
                r = False
                for en in events_enum:
                    if en.has_value(v["type"]) or en.has_value(v["type"].lower()):
                        r = True
                        break
                v["isEvent"] = r
        return value

    return fn
