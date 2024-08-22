# 该代码片段实现了一组用于生成 SQL 查询条件的辅助函数，这些函数帮助根据不同的操作符生成 SQL 语句片段、判断操作符类型、处理多条件查询等。代码通过操作符与 SQL 语句的映射、反转操作符、多条件组合等方式，简化了 SQL 查询的生成过程。
from typing import Union

import schemas
# 根据传入的操作符返回相应的 SQL 运算符
# 参数：
# - op: schemas.SearchEventOperator 或 schemas.ClickEventExtraOperator 类型的操作符
# 返回值：
# - 对应的 SQL 运算符字符串，如果操作符未匹配到，默认返回 "="

def get_sql_operator(op: Union[schemas.SearchEventOperator, schemas.ClickEventExtraOperator]):
    return {
        schemas.SearchEventOperator._is: "=",
        schemas.SearchEventOperator._is_any: "IN",
        schemas.SearchEventOperator._on: "=",
        schemas.SearchEventOperator._on_any: "IN",
        schemas.SearchEventOperator._is_not: "!=",
        schemas.SearchEventOperator._not_on: "!=",
        schemas.SearchEventOperator._contains: "ILIKE",
        schemas.SearchEventOperator._not_contains: "NOT ILIKE",
        schemas.SearchEventOperator._starts_with: "ILIKE",
        schemas.SearchEventOperator._ends_with: "ILIKE",
    }.get(op, "=")

# 判断传入的操作符是否为否定操作符
# 参数：
# - op: schemas.SearchEventOperator 类型的操作符
# 返回值：
# - 布尔值，True 表示该操作符是一个否定操作符，False 表示不是
def is_negation_operator(op: schemas.SearchEventOperator):
    return op in [schemas.SearchEventOperator._is_not, schemas.SearchEventOperator._not_on, schemas.SearchEventOperator._not_contains]

# 反转传入的 SQL 运算符
# 参数：
# - op: 字符串类型的 SQL 运算符（如 "=" 或 "!="）
# 返回值：
# - 反转后的 SQL 运算符字符串
def reverse_sql_operator(op):
    return "=" if op == "!=" else "!=" if op == "=" else "ILIKE" if op == "NOT ILIKE" else "NOT ILIKE"

# 生成多条件查询的 SQL 片段
# 参数：
# - condition: 字符串类型，表示查询条件模板
# - values: 列表类型，包含条件值的列表
# - value_key: 字符串类型，表示条件值的键名（默认值为 "value"）
# - is_not: 布尔类型，表示是否使用 AND 连接条件（默认值为 False）
# 返回值：
# - 组合后的 SQL 查询片段字符串
def multi_conditions(condition, values, value_key="value", is_not=False):
    query = []
    for i in range(len(values)):
        k = f"{value_key}_{i}"
        query.append(condition.replace(value_key, k))
    return "(" + (" AND " if is_not else " OR ").join(query) + ")"

# 将值列表转换为字典格式
# 参数：
# - values: 列表类型，包含条件值的列表
# - value_key: 字符串类型，表示条件值的键名（默认值为 "value"）
# 返回值：
# - 字典类型，键为生成的键名，值为对应的条件值
def multi_values(values, value_key="value"):
    query_values = {}
    if values is not None and isinstance(values, list):
        for i in range(len(values)):
            k = f"{value_key}_{i}"
            query_values[k] = values[i]
    return query_values

# 判断传入的操作符是否为 "ANY" 操作符
# 参数：
# - op: schemas.SearchEventOperator 类型的操作符
# 返回值：
# - 布尔值，True 表示该操作符是 "ANY" 操作符，False 表示不是
def isAny_opreator(op: schemas.SearchEventOperator):
    return op in [schemas.SearchEventOperator._on_any, schemas.SearchEventOperator._is_any]

# 判断传入的操作符是否为 "UNDEFINED" 操作符
# 参数：
# - op: schemas.SearchEventOperator 类型的操作符
# 返回值：
# - 布尔值，True 表示该操作符是 "UNDEFINED" 操作符，False 表示不是
def isUndefined_operator(op: schemas.SearchEventOperator):
    return op in [schemas.SearchEventOperator._is_undefined]
