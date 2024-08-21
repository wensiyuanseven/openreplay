import requests

from decouple import config
# 这段代码定义了一个函数 get_original_trace，用于通过 Sourcemaps 服务获取原始的代码追踪信息。Sourcemaps 是一种帮助开发者调试压缩或编译后的代码的工具。该函数通过向 Sourcemaps 服务发送HTTP请求，获取指定代码位置的原始追踪信息，并返回相应的结果。
SMR_URL = config("sourcemaps_reader").format(config("SMR_KEY", default="smr"))

# 功能描述:
# 该函数用于根据给定的 key 和 positions，从 Sourcemaps 服务获取原始的代码追踪信息。它将信息发送到一个指定的 Sourcemaps 服务器，并返回解析后的 JSON 响应。

# 参数:

# key：用于标识代码的 Sourcemap 的键值。
# positions：要查询的代码位置列表，通常包括行号和列号等信息。
# is_url：一个布尔值，指示 key 是否为一个URL（默认为 False）。
# 返回值:

# 成功时返回包含原始代码追踪信息的 JSON 对象。
# 失败时返回 None，并打印相应的错误信息。
def get_original_trace(key, positions, is_url=False):
    payload = {
        "key": key,
        "positions": positions,
        "padding": 5,
        "bucket": config('sourcemaps_bucket'),
        "isURL": is_url
    }
    try:
        r = requests.post(SMR_URL, json=payload, timeout=config("sourcemapTimeout", cast=int, default=5))
        if r.status_code != 200:
            print(f"Issue getting sourcemap status_code:{r.status_code}")
            return None
        return r.json()
    except requests.exceptions.Timeout:
        print("Timeout getting sourcemap")
        return None
    except Exception as e:
        print("Issue getting sourcemap")
        print(e)
        return None
