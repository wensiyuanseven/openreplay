# 该代码片段提供了一组字符串处理的辅助函数，用于过滤字符串中的无效字符、生成关键字或模式、连接和分割字符串，以及将整数转换为十六进制字符串。这些函数可以用于数据清洗、字符串格式化和处理等场景。
import string


# # 定义一些字符串常量，用于处理字符串格式或拼接
# jsonb = "'::jsonb,'"  # 表示 jsonb 数据类型的字符串片段
# dash = '", "'  # 双引号和逗号的组合，用于拼接字符串
# dash_nl = ",\n"  # 逗号和换行符的组合，用于格式化多行字符串
# dash_key = ")s, %("  # 用于字符串拼接的特殊符号组合
jsonb = "'::jsonb,'"
dash = '", "'
dash_nl = ",\n"
dash_key = ")s, %("

# 过滤字符串中的无效字符并截取指定长度
# 参数：
# - s: 字符串，表示需要过滤的字符串
# - chars: 字符串，包含允许保留的字符集合
# - l: 整型，表示截取的最大长度
# 返回值：
# - 过滤和截取后的字符串，如果过滤后为空，则返回 None
def __filter(s, chars, l):
    s = filter(lambda c: c in chars, s)
    s = "".join(s)
    if len(s) == 0:
        return None
    return s[0:l]

# 定义允许用于关键字的字符集合
__keyword_chars = string.ascii_lowercase + string.ascii_uppercase + string.digits + "_"

# 生成符合关键字规则的字符串
# 参数：
# - s: 字符串，表示需要处理的字符串
# 返回值：
# - 过滤后的关键字字符串，最长为 30 个字符，如果输入不是字符串类型，返回 None
def keyword(s):
    if not isinstance(s, str):
        return None
    s = s.strip().replace(" ", "_")
    return __filter(s, __keyword_chars, 30)

# 定义允许用于模式的字符集合
__pattern_chars = string.ascii_lowercase + string.ascii_uppercase + string.digits + "_-/*."

# 生成符合模式规则的字符串
# 参数：
# - s: 字符串，表示需要处理的字符串
# 返回值：
# - 过滤后的模式字符串，最长为 1000 个字符，如果输入不是字符串类型，返回 None
def pattern(s):
    if not isinstance(s, str):
        return None
    return __filter(s, __pattern_chars, 1000)

# 使用特殊分隔符连接多个字符串
# 参数：
# - *args: 任意数量的字符串参数
# 返回值：
# - 使用 "\x00" 分隔符连接的字符串
def join(*args):
    return "\x00".join(args)

# 使用特殊分隔符分割字符串
# 参数：
# - s: 字符串，表示需要分割的字符串
# 返回值：
# - 分割后的字符串列表
def split(s):
    return s.split("\x00")

# 将整数转换为十六进制字符串
# 参数：
# - n: 整型，表示需要转换的整数
# 返回值：
# - 去掉前缀 "0x" 的十六进制字符串
def hexed(n):
    return hex(n)[2:]
