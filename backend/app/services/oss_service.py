"""
Backblaze B2 对象存储服务封装（S3 兼容 API，使用 boto3）

平滑切换策略：
- B2_KEY_ID / B2_APPLICATION_KEY / B2_BUCKET_NAME 未配置时，is_enabled() 返回 False，所有方法均为空操作
- 调用方在 OSS 上传失败时自动回退到本地存储路径

Backblaze B2 S3 端点格式：
  https://s3.{region}.backblazeb2.com
  例：https://s3.us-west-004.backblazeb2.com
"""
import os
import io
import mimetypes
from typing import Optional
from app.config import get_settings

settings = get_settings()


def _get_content_type(filename: str) -> str:
    """根据文件名推断 Content-Type"""
    mime, _ = mimetypes.guess_type(filename)
    return mime or "application/octet-stream"


class OssService:
    """Backblaze B2 对象存储客户端（boto3 S3 兼容，单例懒加载）"""

    _client = None
    _init_attempted = False

    @classmethod
    def is_enabled(cls) -> bool:
        """是否已配置 B2（密钥和存储桶都不为空才算启用）"""
        return bool(
            settings.B2_KEY_ID
            and settings.B2_APPLICATION_KEY
            and settings.B2_BUCKET_NAME
        )

    @classmethod
    def get_client(cls):
        """惰性初始化 boto3 S3 客户端，未配置或 SDK 未安装则返回 None"""
        if cls._init_attempted:
            return cls._client

        cls._init_attempted = True

        if not cls.is_enabled():
            print("[OSS] B2 未配置，使用本地存储")
            return None

        try:
            import boto3
            from botocore.config import Config

            cls._client = boto3.client(
                service_name="s3",
                endpoint_url=settings.B2_ENDPOINT_URL,
                aws_access_key_id=settings.B2_KEY_ID,
                aws_secret_access_key=settings.B2_APPLICATION_KEY,
                config=Config(signature_version="s3v4"),
            )
            print(
                f"[OSS] B2 客户端初始化成功: bucket={settings.B2_BUCKET_NAME}, "
                f"endpoint={settings.B2_ENDPOINT_URL}"
            )
        except ImportError:
            print("[OSS] 警告: boto3 未安装，请执行 pip install boto3")
        except Exception as e:
            print(f"[OSS] B2 客户端初始化失败: {e}")

        return cls._client

    @classmethod
    def get_public_url(cls, oss_key: str) -> str:
        """根据 oss_key 生成公网访问 URL"""
        if settings.B2_CDN_DOMAIN:
            domain = settings.B2_CDN_DOMAIN.rstrip("/")
            return f"{domain}/{oss_key}"
        # B2 S3 兼容公网 URL 格式：{endpoint}/{bucket}/{key}
        endpoint = settings.B2_ENDPOINT_URL.rstrip("/")
        return f"{endpoint}/{settings.B2_BUCKET_NAME}/{oss_key}"

    @classmethod
    def upload_file(cls, local_path: str, oss_key: str) -> Optional[str]:
        """
        上传本地文件到 B2。

        Args:
            local_path: 本地文件绝对路径
            oss_key:    B2 对象键，如 "images/abc123.jpg"

        Returns:
            成功返回公网 URL，失败返回 None
        """
        client = cls.get_client()
        if not client:
            return None

        try:
            content_type = _get_content_type(local_path)
            with open(local_path, "rb") as f:
                client.put_object(
                    Bucket=settings.B2_BUCKET_NAME,
                    Key=oss_key,
                    Body=f,
                    ContentType=content_type,
                )
            url = cls.get_public_url(oss_key)
            print(f"[OSS] 上传成功: {oss_key} -> {url}")
            return url
        except Exception as e:
            print(f"[OSS] 上传文件失败 ({oss_key}): {e}")
            return None

    @classmethod
    def upload_bytes(cls, data: bytes, oss_key: str, content_type: str = "application/octet-stream") -> Optional[str]:
        """
        直接上传二进制内容到 B2（无需先写本地文件）。

        Args:
            data:         二进制内容
            oss_key:      B2 对象键
            content_type: MIME 类型

        Returns:
            成功返回公网 URL，失败返回 None
        """
        client = cls.get_client()
        if not client:
            return None

        try:
            client.put_object(
                Bucket=settings.B2_BUCKET_NAME,
                Key=oss_key,
                Body=io.BytesIO(data),
                ContentType=content_type,
            )
            url = cls.get_public_url(oss_key)
            print(f"[OSS] 上传成功(bytes): {oss_key} -> {url}")
            return url
        except Exception as e:
            print(f"[OSS] 上传 bytes 失败 ({oss_key}): {e}")
            return None

    @classmethod
    def download_stream(cls, oss_key: str, local_path: str, chunk_size: int = 256 * 1024) -> bool:
        """
        从 B2 流式下载文件到本地路径。

        Args:
            oss_key:    B2 对象键
            local_path: 目标本地文件路径
            chunk_size: 每次读取的字节数（默认 256KB）

        Returns:
            成功返回 True，失败（包括对象不存在）返回 False
        """
        client = cls.get_client()
        if not client:
            return False

        try:
            response = client.get_object(
                Bucket=settings.B2_BUCKET_NAME,
                Key=oss_key,
            )
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, "wb") as f:
                body = response["Body"]
                while True:
                    chunk = body.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
            return True
        except Exception as e:
            # 文件不存在或下载失败，清理可能写了一半的残留
            if os.path.exists(local_path):
                os.remove(local_path)
            print(f"[OSS] 下载失败 ({oss_key}): {e}")
            return False

    @classmethod
    def object_exists(cls, oss_key: str) -> bool:
        """检查 B2 上是否已存在该对象（用于避免重复上传）"""
        client = cls.get_client()
        if not client:
            return False
        try:
            client.head_object(Bucket=settings.B2_BUCKET_NAME, Key=oss_key)
            return True
        except Exception:
            return False
