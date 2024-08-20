import math
import random
import re
import string
from typing import Union
from urllib.parse import urlparse

from decouple import config

import schemas
from chalicelib.utils.TimeUTC import TimeUTC


def get_stage_name():
    return "OpenReplay"


# 这个函数会生成一个由 length 个随机选择的十六进制字符（即数字 0-9 和字母 a-f 或 A-F）组成的字符串。
def random_string(length: int = 36):
    # "".join() 是一个字符串方法，它将一个可迭代对象（例如列表中的字符）连接成一个字符串。
    # random.choices() 是 random 模块中的一个函数，用于从指定的序列中随机选择若干元素。它的第一个参数是可以选择的字符集合，第二个参数 k=length 指定了选择的字符数，这里由 length 参数决定。
    # string.hexdigits 是 string 模块中的一个属性，它包含所有十六进制字符，即 '0123456789abcdefABCDEF'。
    return "".join(random.choices(string.hexdigits, k=length))


# 用于将列表中的字典转换为驼峰命 例如，my_variable_name 转换为驼峰命名后为 myVariableName。 如果 flatten=True，则还会将嵌套的字典扁平化
def list_to_camel_case(items: list[dict], flatten: bool = False) -> list[dict]:
    # 如果 items = ['a', 'b', 'c']，那么 len(items) 将返回 3，range(len(items)) 将生成 range(0, 3)，即 [0, 1, 2]。
    for i in range(len(items)):
        if flatten:
            # 扁平化
            items[i] = flatten_nested_dicts(items[i])
        items[i] = dict_to_camel_case(items[i])

    return items


def dict_to_camel_case(variable, delimiter="_", ignore_keys=[]):
    if variable is None:
        return None
    if isinstance(variable, str):
        return variable
    elif isinstance(variable, dict):
        aux = {}
        for key in variable.keys():
            if key in ignore_keys:
                aux[key] = variable[key]
            elif isinstance(variable[key], dict):
                # dict递归 内部的都会转化成大写
                aux[key_to_camel_case(key, delimiter)] = dict_to_camel_case(variable[key])
            elif isinstance(variable[key], list):
                # list 递归  内部的都会转化成大写
                aux[key_to_camel_case(key, delimiter)] = list_to_camel_case(variable[key])
            else:
                # 驼峰
                aux[key_to_camel_case(key, delimiter)] = variable[key]
        return aux
    else:
        return variable


def dict_to_CAPITAL_keys(variable):
    if variable is None:
        return None
    if isinstance(variable, str):
        return variable.upper()
    elif isinstance(variable, dict):
        aux = {}
        for key in variable.keys():
            if isinstance(variable[key], dict):
                aux[key.upper()] = dict_to_CAPITAL_keys(variable[key])
            else:
                aux[key.upper()] = variable[key]
        return aux
    else:
        return variable


def variable_to_snake_case(variable, delimiter="_", split_number=False):
    if isinstance(variable, str):
        return key_to_snake_case(variable, delimiter, split_number)
    elif isinstance(variable, dict):
        aux = {}
        for key in variable.keys():
            if isinstance(variable[key], dict):
                aux[key_to_snake_case(key, delimiter, split_number)] = variable_to_snake_case(variable[key], delimiter, split_number)
            else:
                aux[key_to_snake_case(key, delimiter, split_number)] = variable[key]
        return aux
    else:
        return variable


def key_to_camel_case(snake_str, delimiter="_"):
    # 检查 snake_str 是否以分隔符（如 _）开头
    if snake_str.startswith(delimiter):
        # 如果字符串以分隔符开头，则将其删除。snake_str[1:] 表示从字符串的第二个字符开始截取，忽略第一个字符
        snake_str = snake_str[1:]
        print(
            delimiter,
        )
    components = snake_str.split(delimiter)
    return components[0] + "".join(x.title() for x in components[1:])


# 示例
# key_to_snake_case("CamelCaseExample")  ==>  camel_case_example
# key_to_snake_case("CamelCaseExample123", split_number=True)  ==>  camel_case_example_123
def key_to_snake_case(name, delimiter="_", split_number=False):
    # re.sub() 是 re 模块中的一个函数，用于将字符串中与正则表达式模式匹配的部分替换为另一个字符串。
    s1 = re.sub("(.)([A-Z][a-z]+)", rf"\1{delimiter}\2", name)
    return re.sub("([a-z])([A-Z0-9])" if split_number else "([a-z0-9])([A-Z])", rf"\1{delimiter}\2", s1).lower()


TRACK_TIME = True


def allow_captcha():
    return config("captcha_server", default=None) is not None and config("captcha_key", default=None) is not None and len(config("captcha_server")) > 0 and len(config("captcha_key")) > 0


# 得用户输入的搜索模式能够在SQL查询中使用，并且能够更灵活地匹配符合条件的字符串
def string_to_sql_like(value):
    #  使用正则表达式将字符串 value 中的多个连续空格替换为单个空格。
    value = re.sub(" +", " ", value)
    value = value.replace("*", "%")
    if value.startswith("^"):
        value = value[1:]
    elif not value.startswith("%"):
        value = "%" + value

    if value.endswith("$"):
        value = value[:-1]
    elif not value.endswith("%"):
        value = value + "%"
    # value = value.replace(" ", "%")
    return value


def string_to_sql_like_with_op(value, op):
    if isinstance(value, list):
        r = []
        for v in value:
            r.append(string_to_sql_like_with_op(v, op))
        return r
    else:
        _value = value
        if _value is None:
            return _value
        if op.upper() != "ILIKE":
            return _value.replace("%", "%%")
        _value = _value.replace("*", "%")
        if _value.startswith("^"):
            _value = _value[1:]
        elif not _value.startswith("%"):
            _value = "%" + _value

        if _value.endswith("$"):
            _value = _value[:-1]
        elif not _value.endswith("%"):
            _value = _value + "%"
        return _value.replace("%", "%%")


likable_operators = [schemas.SearchEventOperator._starts_with, schemas.SearchEventOperator._ends_with, schemas.SearchEventOperator._contains, schemas.SearchEventOperator._not_contains]


def is_likable(op: schemas.SearchEventOperator):
    return op in likable_operators


def values_for_operator(value: Union[str, list], op: schemas.SearchEventOperator):
    if not is_likable(op):
        return value
    if isinstance(value, list):
        r = []
        for v in value:
            r.append(values_for_operator(v, op))
        return r
    else:
        if value is None:
            return value
        if op == schemas.SearchEventOperator._starts_with:
            return f"{value}%"
        elif op == schemas.SearchEventOperator._ends_with:
            return f"%{value}"
        elif op == schemas.SearchEventOperator._contains or op == schemas.SearchEventOperator._not_contains:
            return f"%{value}%"
    return value


# 用于检查一个字符串是否只包含字母（大小写）、空格和连字符（-）
# print(is_alphabet_space_dash("Hello World"))  # 输出 True
# print(is_alphabet_space_dash("Hello-World"))  # 输出 True
# print(is_alphabet_space_dash("Hello123"))     # 输出 False
# print(is_alphabet_space_dash("Hello@World"))  # 输出 False
def is_alphabet_space_dash(word):
    # re.compile("^[a-zA-Z -]*$") 用于编译一个正则表达式模式，并返回一个正则表达式对象 r，可以用于匹配操作
    r = re.compile("^[a-zA-Z -]*$")
    # 使用编译后的正则表达式对象 r 来检查字符串 word 是否完全匹配正则表达式模式。
    return r.match(word) is not None


def merge_lists_by_key(l1, l2, key):
    merged = {}
    for item in l1 + l2:
        if item[key] in merged:
            merged[item[key]].update(item)
        else:
            merged[item[key]] = item
    return [val for (_, val) in merged.items()]


# 用于将嵌套的字典展平成一个平铺的字典
def flatten_nested_dicts(obj):
    if obj is None:
        return None
    result = {}
    for key in obj.keys():
        if isinstance(obj[key], dict):
            # 对象合并 将 result 和 nested_result 中的所有键值对解包并合并成一个新的字典
            result = {**result, **flatten_nested_dicts(obj[key])}
        else:
            result[key] = obj[key]
    return result


def delete_keys_from_dict(d, to_delete):
    if isinstance(to_delete, str):
        to_delete = [to_delete]
    if isinstance(d, dict):
        # set 的主要用途： 用于去除重复元素并提供快速查找操作。
        for single_to_delete in set(to_delete):
            if single_to_delete in d:
                del d[single_to_delete]
        for k, v in d.items():
            delete_keys_from_dict(v, to_delete)
    elif isinstance(d, list):
        for i in d:
            delete_keys_from_dict(i, to_delete)
    return d


def explode_widget(data, key=None):
    result = []
    for k in data.keys():
        if k.endswith("Progress") or k == "chart":
            continue
        result.append({"key": key_to_snake_case(k) if key is None else key, "data": {"value": data[k]}})
        if k + "Progress" in data:
            result[-1]["data"]["progress"] = data[k + "Progress"]
        if "chart" in data:
            result[-1]["data"]["chart"] = []
            for c in data["chart"]:
                result[-1]["data"]["chart"].append({"timestamp": c["timestamp"], "value": c[k]})
    return result


# 第一个 issue_type 是传入的参数，字典将使用这个参数作为键来查找对应的值。
# 第二个 issue_type 是 get 方法的默认值。如果字典中没有找到传入的 issue_type，则返回这个默认值。
def get_issue_title(issue_type):
    return {
        "click_rage": "Click Rage",
        "dead_click": "Dead Click",
        "excessive_scrolling": "Excessive Scrolling",
        "bad_request": "Bad Request",
        "missing_resource": "Missing Image",
        "memory": "High Memory Usage",
        "cpu": "High CPU",
        "slow_resource": "Slow Resource",
        "slow_page_load": "Slow Page",
        "crash": "Crash",
        "ml_cpu": "High CPU",
        "ml_memory": "High Memory Usage",
        "ml_dead_click": "Dead Click",
        "ml_click_rage": "Click Rage",
        "ml_mouse_thrashing": "Mouse Thrashing",
        "ml_excessive_scrolling": "Excessive Scrolling",
        "ml_slow_resources": "Slow Resource",
        "custom": "Custom Event",
        "js_exception": "Error",
        "custom_event_error": "Custom Error",
        "js_error": "Error",
        "mouse_thrashing": "Mouse Thrashing",
    }.get(issue_type, issue_type)


def __progress(old_val, new_val):
    return ((old_val - new_val) / new_val) * 100 if new_val > 0 else 0 if old_val == 0 else 100


def __decimal_limit(value, limit):
    factor = pow(10, limit)
    value = math.floor(value * factor)
    if value % factor == 0:
        return value // factor
    return value / factor


# 这个函数的作用是将输入的包含 "events" 和 "filters" 的字典进行处理，将 "events" 中的每个元素标记为事件（"isEvent": True），将 "filters" 中的每个元素标记为非事件（"isEvent": False），然后将它们合并到同一个列表中，存储在 "filters" 键下，最后返回修改后的字典。
def old_search_payload_to_flat(values):
    # in case the old search body was passed
    # 如果 "events" 不存在，不会抛出错误，而是返回 None 如果不是 None，则表示存在有效数据。
    if values.get("events") is not None:
        for v in values["events"]:
            #  为每个事件（v）添加一个新的键值对 "isEvent": True，标记这个元素是一个事件
            v["isEvent"] = True
            # 如果 "filters" 键不存在，则使用一个空列表 [] 作为默认值，避免抛出错误。
        for v in values.get("filters", []):
            # v["isEvent"] = False 为每个过滤器元素添加一个新的键值对 "isEvent": False，标记这个元素不是事件。
            v["isEvent"] = False
        # 合并 events 和 filters 列表：
        # values.pop("events") 从 values 字典中删除 "events" 键，并返回它对应的列表。
        values["filters"] = values.pop("events") + values.get("filters", [])
    return values


def custom_alert_to_front(values):
    # to support frontend format for payload
    if values.get("seriesId") is not None and values["query"]["left"] == schemas.AlertColumn.custom:
        values["query"]["left"] = values["seriesId"]
        values["seriesId"] = None
    return values


def __time_value(row):
    row["unit"] = schemas.TemplatePredefinedUnits.millisecond
    factor = 1
    if row["value"] > TimeUTC.MS_MINUTE:
        row["value"] = row["value"] / TimeUTC.MS_MINUTE
        row["unit"] = schemas.TemplatePredefinedUnits.minute
        factor = TimeUTC.MS_MINUTE
    elif row["value"] > 1 * 1000:
        row["value"] = row["value"] / 1000
        row["unit"] = schemas.TemplatePredefinedUnits.second
        factor = 1000

    if "chart" in row and factor > 1:
        for r in row["chart"]:
            r["value"] /= factor


def is_saml2_available():
    return config("hastSAML2", default=False, cast=bool)


def get_domain():
    _url = config("SITE_URL")
    if not _url.startswith("http"):
        _url = "http://" + _url
    return ".".join(urlparse(_url).netloc.split(".")[-2:])


def obfuscate(text, keep_last: int = 4):
    if text is None or not isinstance(text, str):
        return text
    if len(text) <= keep_last:
        return "*" * len(text)
    return "*" * (len(text) - keep_last) + text[-keep_last:]


def cast_session_id_to_string(data):
    if not isinstance(data, dict) and not isinstance(data, list):
        return data
    if isinstance(data, list):
        for i, item in enumerate(data):
            data[i] = cast_session_id_to_string(item)
    elif isinstance(data, dict):
        keys = data.keys()
        if "sessionId" in keys:
            data["sessionId"] = str(data["sessionId"])
        else:
            for key in keys:
                data[key] = cast_session_id_to_string(data[key])
    return data
