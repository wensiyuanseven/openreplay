# 这段代码实现了一系列函数，主要用于处理 JavaScript 的 Sourcemaps 文件。这些函数的功能包括生成预签名的共享和上传 URL、格式化和验证堆栈帧、
# 获取和处理 Sourcemaps 文件以及填充丢失的上下文信息。它们共同用于解析错误日志中的压缩 JavaScript 代码，并恢复出原始的源代码位置，帮助开发者定位错误的源头。
from urllib.parse import urlparse

import requests
from decouple import config

from chalicelib.core import sourcemaps_parser
from chalicelib.utils.storage import StorageClient, generators

# 功能描述:
# 为指定的 URL 生成预签名的共享链接，供用户下载或查看。
# 参数:
# project_id: 项目ID，用于区分不同项目的文件。
# urls: 一个包含多个URL的列表，这些URL代表需要生成预签名链接的文件。
# 返回值:
# 返回一个列表，列表中的每个元素都是生成的预签名URL。
def presign_share_urls(project_id, urls):
    results = []
    for u in urls:
        results.append(StorageClient.get_presigned_url_for_sharing(bucket=config('sourcemaps_bucket'), expires_in=120,
                                                               key=generators.generate_file_key_from_url(project_id, u),
                                                               check_exists=True))
    return results

# 功能描述:
# 为指定的 URL 生成预签名的上传链接，使得客户端可以将文件上传到指定的位置。
# 参数:
# project_id: 项目ID，用于区分不同项目的文件。
# urls: 一个包含多个URL的列表，这些URL代表需要生成预签名上传链接的文件。
# 返回值:
# 返回一个列表，列表中的每个元素都是生成的预签名上传URL。
def presign_upload_urls(project_id, urls):
    results = []
    for u in urls:
        results.append(StorageClient.get_presigned_url_for_upload(bucket=config('sourcemaps_bucket'),
                                                              expires_in=1800,
                                                              key=generators.generate_file_key_from_url(project_id, u)))
    return results

# 功能描述:
# 将旧格式的堆栈帧信息转换为新的标准化格式。
# 参数:
# f: 一个字典，包含旧格式的堆栈帧信息。
# 返回值:
# 返回格式化后的堆栈帧字典。
def __format_frame_old(f):
    if f.get("context") is None:
        f["context"] = []
    else:
        f["context"] = [[f["line"], f["context"]]]
    url = f.pop("url")
    f["absPath"] = url
    f["filename"] = urlparse(url).path
    f["lineNo"] = f.pop("line")
    f["colNo"] = f.pop("column")
    f["function"] = f.pop("func")
    return f

# 功能描述:
# 检查堆栈帧是否包含有效的关键信息（行号、列号、文件名）。
# 参数:
# f: 一个字典，表示一个堆栈帧。
# 返回值:
# 如果堆栈帧有效，返回 True，否则返回 False。
def __frame_is_valid(f):
    return "columnNumber" in f and \
           "lineNumber" in f and \
           "fileName" in f

# 功能描述:
# 将新的堆栈帧信息格式化为标准化格式，适用于新的输入数据结构。
# 参数:
# f: 一个字典，包含堆栈帧的信息。
# 返回值:
# 返回格式化后的堆栈帧字典。
def __format_frame(f):
    f["context"] = []  # no context by default
    if "source" in f:
        f.pop("source")
    url = f.pop("fileName")
    f["absPath"] = url
    f["filename"] = urlparse(url).path
    f["lineNo"] = f.pop("lineNumber")
    f["colNo"] = f.pop("columnNumber")
    f["function"] = f.pop("functionName") if "functionName" in f else None
    return f

# 功能描述:
# 将整个 payload 中的所有堆栈帧信息进行格式化，并支持只格式化第一个帧。
# 参数:
# p: 要格式化的 payload，可能是一个堆栈帧列表或包含堆栈帧的字典。
# truncate_to_first: 布尔值，指示是否只格式化第一个堆栈帧。
# 返回值:
# 返回格式化后的堆栈帧列表。
def format_payload(p, truncate_to_first=False):
    if type(p) is list:
        return [__format_frame(f) for f in (p[:1] if truncate_to_first else p) if __frame_is_valid(f)]
    if type(p) is dict:
        stack = p.get("stack", [])
        return [__format_frame_old(f) for f in (stack[:1] if truncate_to_first else stack)]
    return []


def url_exists(url):
    try:
        r = requests.head(url, allow_redirects=False)
        return r.status_code == 200 and "text/html" not in r.headers.get("Content-Type", "")
    except Exception as e:
        print(f"!! Issue checking if URL exists: {url}")
        print(e)
        return False

# 功能描述:
# 检查给定的 URL 是否存在。
# 参数:
# url: 要检查的 URL。
# 返回值:
# 如果 URL 存在且有效，返回 True，否则返回 False。
def get_traces_group(project_id, payload):
    frames = format_payload(payload)

    results = [{}] * len(frames)
    payloads = {}
    all_exists = True
    for i, u in enumerate(frames):
        file_exists_in_bucket = False
        file_exists_in_server = False
        file_url = u["absPath"]
        key = generators.generate_file_key_from_url(project_id, file_url)  # use filename instead?
        params_idx = file_url.find("?")
        if file_url and len(file_url) > 0 \
                and not (file_url[:params_idx] if params_idx > -1 else file_url).endswith(".js"):
            print(f"{u['absPath']} sourcemap is not a JS file")
            payloads[key] = None

        if key not in payloads:
            file_exists_in_bucket = len(file_url) > 0 and StorageClient.exists(config('sourcemaps_bucket'), key)
            if len(file_url) > 0 and not file_exists_in_bucket:
                print(f"{u['absPath']} sourcemap (key '{key}') doesn't exist in S3 looking in server")
                if not file_url.endswith(".map"):
                    file_url += '.map'
                file_exists_in_server = url_exists(file_url)
                file_exists_in_bucket = file_exists_in_server
            all_exists = all_exists and file_exists_in_bucket
            if not file_exists_in_bucket and not file_exists_in_server:
                print(f"{u['absPath']} sourcemap (key '{key}') doesn't exist in S3 nor server")
                payloads[key] = None
            else:
                payloads[key] = []
        results[i] = dict(u)
        results[i]["frame"] = dict(u)
        if payloads[key] is not None:
            payloads[key].append({"resultIndex": i, "frame": dict(u), "URL": file_url,
                                  "position": {"line": u["lineNo"], "column": u["colNo"]},
                                  "isURL": file_exists_in_server})

    for key in payloads.keys():
        if payloads[key] is None:
            continue
        key_results = sourcemaps_parser.get_original_trace(
            key=payloads[key][0]["URL"] if payloads[key][0]["isURL"] else key,
            positions=[o["position"] for o in payloads[key]],
            is_url=payloads[key][0]["isURL"])
        if key_results is None:
            all_exists = False
            continue
        for i, r in enumerate(key_results):
            res_index = payloads[key][i]["resultIndex"]
            # function name search  by frontend lib is better than sourcemaps' one in most cases
            if results[res_index].get("function") is not None:
                r["function"] = results[res_index]["function"]
            r["frame"] = payloads[key][i]["frame"]
            results[res_index] = r
    return fetch_missed_contexts(results), all_exists

# 功能描述:
# 生成 JavaScript 文件的缓存路径，用于从存储中检索文件。
# 参数:
# fullURL: JavaScript 文件的完整 URL。
# 返回值:
# 返回生成的缓存路径。
def get_js_cache_path(fullURL):
    p = urlparse(fullURL)
    return p.scheme + '/' + p.netloc + p.path  # TODO (Also in go assets library): What if URL with query? (like versions)


MAX_COLUMN_OFFSET = 60

# 功能描述:
# 为缺失上下文信息的堆栈帧填充源代码上下文，从存储中检索对应的文件，并根据行号和列号提取源代码的相关部分。
# 参数:
# frames: 一个包含堆栈帧信息的列表。
# 返回值:
# 返回填充了上下文信息的堆栈帧列表。
def fetch_missed_contexts(frames):
    source_cache = {}
    for i in range(len(frames)):
        if frames[i] and frames[i].get("context") and len(frames[i]["context"]) > 0:
            continue
        file_abs_path = frames[i]["frame"]["absPath"]
        if file_abs_path in source_cache:
            file = source_cache[file_abs_path]
        else:
            file_path = get_js_cache_path(file_abs_path)
            file = StorageClient.get_file(config('js_cache_bucket'), file_path)
            if file is None:
                print(f"Missing abs_path: {file_abs_path}, file {file_path} not found in {config('js_cache_bucket')}")
            source_cache[file_abs_path] = file
        if file is None:
            continue
        lines = file.split("\n")

        if frames[i]["lineNo"] is None:
            print("no original-source found for frame in sourcemap results")
            frames[i] = frames[i]["frame"]
            frames[i]["originalMapping"] = False

        l = frames[i]["lineNo"] - 1  # starts from 1
        c = frames[i]["colNo"] - 1  # starts from 1
        if len(lines) == 1:
            print(f"minified asset")
            l = frames[i]["frame"]["lineNo"] - 1  # starts from 1
            c = frames[i]["frame"]["colNo"] - 1  # starts from 1
        elif l >= len(lines):
            print(f"line number {l} greater than file length {len(lines)}")
            continue

        line = lines[l]
        offset = c - MAX_COLUMN_OFFSET
        if offset < 0:  # if the line is short
            offset = 0
        frames[i]["context"].append([frames[i]["lineNo"], line[offset: c + MAX_COLUMN_OFFSET + 1]])
    return frames
