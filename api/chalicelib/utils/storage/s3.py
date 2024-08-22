# 这段代码实现了一个与 Amazon S3 交互的存储类 AmazonS3Storage，它继承了前面定义的 ObjectStorage 抽象基类。
# 该类提供了一系列方法用于操作 S3 存储桶中的文件，如检查文件是否存在、生成预签名 URL、获取文件内容和标记文件以供删除等。
import boto3
import botocore
from botocore.client import Config
from botocore.exceptions import ClientError
from decouple import config
from requests.models import PreparedRequest
from chalicelib.utils.storage.interface import ObjectStorage


# 功能描述:
# 该类是与 Amazon S3 进行交互的具体实现。它封装了 boto3 客户端的操作，使得上层代码可以方便地进行文件的上传、下载和管理。
# 静态属性 client 和 resource
# 功能描述:
# 这些属性是 boto3 的客户端和资源对象，用于与 S3 进行通信。它们根据配置来决定是否使用自定义的 S3 主机（如用于本地开发或私有 S3 兼容服务）。
class AmazonS3Storage(ObjectStorage):
    if not config("S3_HOST", default=False):
        client = boto3.client("s3")
        resource = boto3.resource("s3")
    else:
        client = boto3.client("s3", endpoint_url=config("S3_HOST"), aws_access_key_id=config("S3_KEY"), aws_secret_access_key=config("S3_SECRET"), config=Config(signature_version="s3v4"), region_name=config("sessions_region"), verify=not config("S3_DISABLE_SSL_VERIFY", default=False, cast=bool))
        resource = boto3.resource("s3", endpoint_url=config("S3_HOST"), aws_access_key_id=config("S3_KEY"), aws_secret_access_key=config("S3_SECRET"), config=Config(signature_version="s3v4"), region_name=config("sessions_region"), verify=not config("S3_DISABLE_SSL_VERIFY", default=False, cast=bool))

    # 功能描述:
    # 检查指定的对象是否存在于 S3 存储桶中。
    # 参数:
    # bucket (str): 存储桶的名称。
    # key (str): 对象的键（路径）。
    # 返回值:
    # 如果对象存在，返回 True；否则返回 False。
    def exists(self, bucket, key):
        try:
            self.resource.Object(bucket, key).load()
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            else:
                # Something else has gone wrong.
                raise
        return True

    # 功能描述:
    # 为指定的对象生成一个预签名的 URL，用于下载该对象。
    # 参数:
    # bucket (str): 存储桶的名称。
    # expires_in (int): URL 的有效期（秒）。
    # key (str): 对象的键（路径）。
    # check_exists (bool): 是否在生成 URL 之前检查对象是否存在。
    # 返回值:
    # 返回生成的预签名 URL，如果对象不存在且 check_exists 为 True，则返回 None。
    def get_presigned_url_for_sharing(self, bucket, expires_in, key, check_exists=False):
        if check_exists and not self.exists(bucket, key):
            return None

        return self.client.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=expires_in)

    # 功能描述:
    # 为指定的对象生成一个预签名的 URL，用于上传该对象。
    # 参数:
    # bucket (str): 存储桶的名称。
    # expires_in (int): URL 的有效期（秒）。
    # key (str): 对象的键（路径）。
    # **args: 其他可选参数。
    # 返回值:
    # 返回生成的预签名 URL。
    def get_presigned_url_for_upload(self, bucket, expires_in, key, **args):
        return self.client.generate_presigned_url("put_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=expires_in)

    # 生成一个安全的预签名 URL，用于上传对象，并允许设置访问控制权限（ACL）和内容类型。
    # 参数:
    # bucket (str): 存储桶的名称。
    # expires_in (int): URL 的有效期（秒）。
    # key (str): 对象的键（路径）。
    # conditions (list): 附加的条件，用于限制上传。
    # public (bool): 如果为 True，生成的 URL 允许公开访问。
    # content_type (str): 上传内容的 MIME 类型。
    # 返回值:
    # 返回生成的预签名 URL。
    def get_presigned_url_for_upload_secure(self, bucket, expires_in, key, conditions=None, public=False, content_type=None):
        acl = "private"
        if public:
            acl = "public-read"
        fields = {"acl": acl}
        if content_type:
            fields["Content-Type"] = content_type
        url_parts = self.client.generate_presigned_post(
            Bucket=bucket,
            Key=key,
            ExpiresIn=expires_in,
            Fields=fields,
            Conditions=conditions,
        )
        req = PreparedRequest()
        req.prepare_url(f"{url_parts['url']}/{url_parts['fields']['key']}", url_parts["fields"])
        return req.url

    # 功能描述:
    # 从 S3 存储桶中获取指定对象的内容。
    # 参数:
    # source_bucket (str): 源存储桶的名称。
    # source_key (str): 源对象的键（路径）。
    # 返回值:
    # 返回文件内容的字节数组，如果文件不存在，返回 None。
    def get_file(self, source_bucket, source_key):
        try:
            result = self.client.get_object(Bucket=source_bucket, Key=source_key)
        except ClientError as ex:
            if ex.response["Error"]["Code"] == "NoSuchKey":
                return None
            else:
                raise ex
        return result["Body"].read().decode()

    # 为指定的对象添加一个特殊标记，表明该对象将在指定天数后被删除。
    # 参数:
    # bucket (str): 存储桶的名称。
    # key (str): 对象的键（路径）。
    # 返回值:
    # 如果对象存在并成功标记，返回 True；否则返回 False。
    def tag_for_deletion(self, bucket, key):
        if not self.exists(bucket, key):
            return False
        # Copy the file to change the creation date, so it can be deleted X days after the tag's creation
        s3_target = self.resource.Object(bucket, key)
        s3_target.copy_from(CopySource={"Bucket": bucket, "Key": key}, MetadataDirective="COPY", TaggingDirective="COPY")

        self.tag_file(bucket=bucket, file_key=key, tag_key="to_delete_in_days", tag_value=config("SCH_DELETE_DAYS", default="7"))

    # 功能描述:
    # 为指定对象添加一个标签，用于标记对象的状态或用途。
    # 参数:
    # file_key (str): 文件的键（路径）。
    # bucket (str): 存储桶的名称。
    # tag_key (str): 标签的键。
    # tag_value (str): 标签的值。
    # 返回值:
    # 返回标签操作的结果。
    def tag_file(self, file_key, bucket, tag_key, tag_value):
        return self.client.put_object_tagging(
            Bucket=bucket,
            Key=file_key,
            Tagging={
                "TagSet": [
                    {"Key": tag_key, "Value": tag_value},
                ]
            },
        )
