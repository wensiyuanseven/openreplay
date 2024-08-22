from abc import ABC, abstractmethod

# 代码定义了一个抽象基类 ObjectStorage，用于描述与对象存储（如云存储系统）交互的接口。这个接口定义了一些常见的存储操作，
# 如检查文件是否存在、获取文件、生成预签名 URL 以及标记文件以供删除。这些方法是抽象的，意味着任何继承这个类的具体存储实现都必须提供这些方法的具体实现。

# 这是一个抽象基类，用于定义与对象存储系统交互的接口。所有继承 ObjectStorage 的类必须实现这些接口。


class ObjectStorage(ABC):
    @abstractmethod
    # 功能描述:
    # 检查指定的对象（文件）是否存在于存储桶中。
    # 参数:
    # bucket (str): 存储桶的名称。
    # key (str): 对象的键（路径）。
    # 返回值:
    # 返回 True 如果对象存在，否则返回 False。
    def exists(self, bucket, key):
        # Returns True if the object exists in the bucket, False otherwise
        pass

    @abstractmethod
    #     功能描述:
    # 下载并返回指定对象的内容（以字节形式返回）。
    # 参数:
    # source_bucket (str): 源存储桶的名称。
    # source_key (str): 源对象的键（路径）。
    # 返回值:
    # 返回文件内容的字节数组。
    def get_file(self, source_bucket, source_key):
        # Download and returns the file contents as bytes
        pass

    # 抽象方法 get_presigned_url_for_sharing
    # 功能描述:
    # 为指定的对象生成一个预签名的 URL，允许用户在一段时间内下载该对象。
    # 参数:
    # bucket (str): 存储桶的名称。
    # expires_in (int): URL 的有效期（秒）。
    # key (str): 对象的键（路径）。
    # check_exists (bool): 是否在生成 URL 之前检查对象是否存在。
    # 返回值:
    # 返回生成的预签名 URL。
    @abstractmethod
    def get_presigned_url_for_sharing(self, bucket, expires_in, key, check_exists=False):
        # Returns a pre-signed URL for downloading the file from the object storage
        pass

    # 功能描述:
    # 为指定的对象生成一个预签名的 URL，允许用户在一段时间内上传该对象。
    # 参数:
    # bucket (str): 存储桶的名称。
    # expires_in (int): URL 的有效期（秒）。
    # key (str): 对象的键（路径）。
    # **args: 其他可选参数。
    # 返回值:
    # 返回生成的预签名 URL。
    @abstractmethod
    def get_presigned_url_for_upload(self, bucket, expires_in, key, **args):
        # Returns a pre-signed URL for uploading the file to the object storage
        pass

    # 抽象方法 tag_for_deletion
    # 功能描述:
    # 为指定的对象添加一个特殊标记，表明该对象将在指定天数后被删除。
    # 参数:
    # bucket (str): 存储桶的名称。
    # key (str): 对象的键（路径）。
    # 返回值:
    # 无返回值，该方法执行对象的标记操作。
    @abstractmethod
    def tag_for_deletion(self, bucket, key):
        # Adds the special tag 'to_delete_in_days' to the file to mark it for deletion
        pass
