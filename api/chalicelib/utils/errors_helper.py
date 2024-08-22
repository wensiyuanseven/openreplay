from chalicelib.core import sourcemaps
# 代码片段用于格式化错误对象的第一个堆栈帧。具体来说，它首先使用format_payload函数对错误的堆栈信息进行格式化，然后对每个堆栈帧中的上下文字符串进行处理，如果字符串长度超过1000个字符，将其截断。
# 此外，还将堆栈帧中的文件名从字节类型转换为字符串类型。最终，返回经过格式化处理后的错误对象。

# 格式化错误对象的第一个堆栈帧。
# 该函数使用sourcemaps模块中的format_payload函数格式化错误对象的堆栈信息，
# 并处理每个堆栈帧中的上下文字符串和文件名。
# 参数：
# - error: 字典类型（dict），包含错误信息的对象，包括payload和stack等键值对。
# 返回值：
# - error: 格式化后的错误对象，类型为字典（dict）。
def format_first_stack_frame(error):
    # 使用sourcemaps的format_payload函数格式化payload，并将结果存储在error["stack"]中，保留第一个堆栈帧。
    error["stack"] = sourcemaps.format_payload(error.pop("payload"), truncate_to_first=True)
    # 遍历每个堆栈帧，并进一步处理上下文和文件名。
    for s in error["stack"]:
        #  遍历上下文列表中的每个字符串，并截断长度超过1000字符的字符串。
        for c in s.get("context", []):
            for sci, sc in enumerate(c):
                if isinstance(sc, str) and len(sc) > 1000:
                    c[sci] = sc[:1000]
        # convert bytes to string:
        #  将文件名从字节类型转换为字符串类型。
        if isinstance(s["filename"], bytes):
            s["filename"] = s["filename"].decode("utf-8")
    return error
