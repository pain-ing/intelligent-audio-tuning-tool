"""
存储服务实现
"""
import os
import shutil
from typing import Optional
from urllib.parse import urljoin

from src.services.base import BaseService, StorageServiceInterface
from src.core.config import config, StorageMode
from src.core.exceptions import StorageError, ErrorCode

# 提供可被测试替换的 Minio 符号（模块级），便于 unittest.mock.patch
try:
    from minio import Minio as Minio
except Exception:
    Minio = None


class LocalStorageService(BaseService, StorageServiceInterface):
    """本地文件存储服务"""
    
    def __init__(self, base_path: str = "data/storage"):
        super().__init__()
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)
    
    def _get_full_path(self, object_key: str) -> str:
        """获取完整文件路径"""
        return os.path.join(self.base_path, object_key.lstrip('/'))
    
    async def upload_file(self, file_path: str, object_key: str) -> str:
        """上传文件到本地存储"""
        try:
            full_path = self._get_full_path(object_key)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            shutil.copy2(file_path, full_path)
            self.logger.info(f"File uploaded: {file_path} -> {object_key}")
            return object_key
            
        except Exception as e:
            raise StorageError(
                message=f"Failed to upload file: {str(e)}",
                code=ErrorCode.UPLOAD_FAILED,
                detail={"file_path": file_path, "object_key": object_key}
            )
    
    async def download_file(self, object_key: str, file_path: str) -> None:
        """从本地存储下载文件"""
        try:
            full_path = self._get_full_path(object_key)
            
            if not os.path.exists(full_path):
                raise StorageError(
                    message=f"File not found: {object_key}",
                    code=ErrorCode.NOT_FOUND
                )
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            shutil.copy2(full_path, file_path)
            self.logger.info(f"File downloaded: {object_key} -> {file_path}")
            
        except StorageError:
            raise
        except Exception as e:
            raise StorageError(
                message=f"Failed to download file: {str(e)}",
                code=ErrorCode.DOWNLOAD_FAILED,
                detail={"object_key": object_key, "file_path": file_path}
            )
    
    async def delete_file(self, object_key: str) -> None:
        """删除本地存储文件"""
        try:
            full_path = self._get_full_path(object_key)
            
            if os.path.exists(full_path):
                os.unlink(full_path)
                self.logger.info(f"File deleted: {object_key}")
            
        except Exception as e:
            raise StorageError(
                message=f"Failed to delete file: {str(e)}",
                detail={"object_key": object_key}
            )
    
    async def get_download_url(self, object_key: str, expires_in: int = 3600) -> str:
        """获取本地文件的访问URL"""
        # 对于本地存储，返回相对URL
        return f"/files/{object_key}"


class MinIOStorageService(BaseService, StorageServiceInterface):
    """MinIO对象存储服务"""
    
    def __init__(self):
        super().__init__()
        if Minio is None:
            raise StorageError("MinIO client not available")
        try:
            self.client = Minio(
                endpoint=self.config.storage_endpoint,
                access_key=self.config.storage_access_key,
                secret_key=self.config.storage_secret_key,
                secure=False  # 开发环境使用HTTP
            )
            self.bucket = self.config.storage_bucket

            # 确保bucket存在
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
        except Exception as e:
            raise StorageError(f"Failed to initialize MinIO client: {str(e)}")

    async def upload_file(self, file_path: str, object_key: str) -> str:
        """上传文件到MinIO"""
        try:
            self.client.fput_object(self.bucket, object_key, file_path)
            self.logger.info(f"File uploaded to MinIO: {file_path} -> {object_key}")
            return object_key
            
        except Exception as e:
            raise StorageError(
                message=f"Failed to upload file to MinIO: {str(e)}",
                code=ErrorCode.UPLOAD_FAILED,
                detail={"file_path": file_path, "object_key": object_key}
            )
    
    async def download_file(self, object_key: str, file_path: str) -> None:
        """从MinIO下载文件"""
        try:
            dirpath = os.path.dirname(file_path)
            if dirpath:
                os.makedirs(dirpath, exist_ok=True)
            self.client.fget_object(self.bucket, object_key, file_path)
            self.logger.info(f"File downloaded from MinIO: {object_key} -> {file_path}")

        except Exception as e:
            raise StorageError(
                message=f"Failed to download file from MinIO: {str(e)}",
                code=ErrorCode.DOWNLOAD_FAILED,
                detail={"object_key": object_key, "file_path": file_path}
            )
    
    async def delete_file(self, object_key: str) -> None:
        """从MinIO删除文件"""
        try:
            self.client.remove_object(self.bucket, object_key)
            self.logger.info(f"File deleted from MinIO: {object_key}")
            
        except Exception as e:
            raise StorageError(
                message=f"Failed to delete file from MinIO: {str(e)}",
                detail={"object_key": object_key}
            )
    
    async def get_download_url(self, object_key: str, expires_in: int = 3600) -> str:
        """获取MinIO预签名下载URL"""
        try:
            from datetime import timedelta
            url = self.client.presigned_get_object(
                self.bucket,
                object_key,
                expires=timedelta(seconds=expires_in)
            )
            return url
            
        except Exception as e:
            raise StorageError(
                message=f"Failed to generate download URL: {str(e)}",
                detail={"object_key": object_key}
            )


def get_storage_service() -> StorageServiceInterface:
    """获取存储服务实例"""
    if config.storage_mode == StorageMode.LOCAL:
        return LocalStorageService()
    elif config.storage_mode == StorageMode.MINIO:
        return MinIOStorageService()
    else:
        raise StorageError(f"Unsupported storage mode: {config.storage_mode}")
