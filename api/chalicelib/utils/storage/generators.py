import hashlib
from urllib.parse import urlparse

# 这段代码提供了生成文件唯一标识符（文件键）的功能，特别是针对 URL 资源的唯一标识符生成。文件键通常用于在存储系统中管理和查找文件，例如在云存储中管理文件的路径。


# 根据项目 ID 和指定的键生成文件的唯一标识符。生成的文件键是项目 ID 和键的 MD5 哈希值的组合，确保文件键唯一且适合用作存储系统中的路径。
# 参数:
# project_id (int): 项目的唯一标识符，用于区分不同项目的文件。
# key (str): 原始键值，用于生成唯一的文件标识符。
# 返回值:
# 返回一个字符串，格式为 "{project_id}/{md5_hash}"，其中 md5_hash 是原始键的 MD5 哈希值。
def generate_file_key(project_id, key):
    return f"{project_id}/{hashlib.md5(key.encode()).hexdigest()}"

# 功能描述:
# 根据项目 ID 和指定的 URL 生成文件的唯一标识符。函数会从 URL 中提取方案（scheme）、网络位置（netloc）和路径（path），然后使用这些信息生成唯一的文件标识符。
# 参数:
# project_id (int): 项目的唯一标识符，用于区分不同项目的文件。
# url (str): 需要转换为文件键的 URL。
# 返回值:
# 返回一个字符串，格式为 "{project_id}/{md5_hash}"，其中 md5_hash 是从 URL 提取的基本路径信息的 MD5 哈希值。
def generate_file_key_from_url(project_id, url):
    u = urlparse(url)
    new_url = u.scheme + "://" + u.netloc + u.path
    return generate_file_key(project_id=project_id, key=new_url)


# 使用示例：
# 假设你有一个项目 ID 为 1234，并且你想为 URL https://example.com/path/to/resource 生成一个文件键：

# python
# 复制代码
# project_id = 1234
# url = "https://example.com/path/to/resource"
# file_key = generate_file_key_from_url(project_id, url)
# print(file_key)
# 这将输出一个类似于 1234/9b74c9897bac770ffc029102a200c5de 的字符串，其中 9b74c9897bac770ffc029102a200c5de 是 URL 的哈希值。

# 注意事项：
# 使用 MD5 哈希确保了文件键的长度固定，且能较好地分布，避免冲突。
# 生成的文件键可以直接用于文件存储系统中的路径管理。