"""
对象存储服务模块
支持 MinIO、AWS S3、腾讯云 COS 等兼容 S3 的对象存储
"""

import os
import uuid
import hashlib
import mimetypes
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import logging

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from botocore.config import Config

logger = logging.getLogger(__name__)

class StorageService:
    """对象存储服务"""
    
    def __init__(self):
        self.endpoint_url = os.getenv("STORAGE_ENDPOINT_URL", "http://localhost:9000")
        self.access_key = os.getenv("STORAGE_ACCESS_KEY", "minioadmin")
        self.secret_key = os.getenv("STORAGE_SECRET_KEY", "minioadmin")
        self.bucket_name = os.getenv("STORAGE_BUCKET_NAME", "audio-files")
        self.region = os.getenv("STORAGE_REGION", "us-east-1")
        
        # 配置 S3 客户端
        self.config = Config(
            region_name=self.region,
            retries={'max_attempts': 3, 'mode': 'adaptive'},
            max_pool_connections=50
        )
        
        try:
            self.s3_client = boto3.client(
                's3',
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                config=self.config
            )
            
            # 确保存储桶存在
            self._ensure_bucket_exists()
            
            logger.info(f"Storage service initialized: {self.endpoint_url}/{self.bucket_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize storage service: {e}")
            raise
    
    def _ensure_bucket_exists(self):
        """确保存储桶存在"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Bucket {self.bucket_name} exists")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                # 存储桶不存在，创建它
                try:
                    if self.region == 'us-east-1':
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                    else:
                        self.s3_client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': self.region}
                        )
                    
                    # 设置 CORS 策略
                    self._set_bucket_cors()
                    
                    logger.info(f"Created bucket: {self.bucket_name}")
                except ClientError as create_error:
                    logger.error(f"Failed to create bucket: {create_error}")
                    raise
            else:
                logger.error(f"Error checking bucket: {e}")
                raise
    
    def _set_bucket_cors(self):
        """设置存储桶 CORS 策略"""
        cors_configuration = {
            'CORSRules': [
                {
                    'AllowedHeaders': ['*'],
                    'AllowedMethods': ['GET', 'PUT', 'POST', 'DELETE', 'HEAD'],
                    'AllowedOrigins': ['*'],
                    'ExposeHeaders': ['ETag', 'x-amz-request-id'],
                    'MaxAgeSeconds': 3600
                }
            ]
        }
        
        try:
            self.s3_client.put_bucket_cors(
                Bucket=self.bucket_name,
                CORSConfiguration=cors_configuration
            )
            logger.info("CORS configuration set for bucket")
        except ClientError as e:
            logger.warning(f"Failed to set CORS configuration: {e}")
    
    def generate_object_key(self, file_extension: str, prefix: str = "uploads") -> str:
        """生成对象存储键名"""
        timestamp = datetime.now().strftime("%Y%m%d")
        unique_id = str(uuid.uuid4())
        
        # 确保扩展名以点开头
        if not file_extension.startswith('.'):
            file_extension = '.' + file_extension
        
        return f"{prefix}/{timestamp}/{unique_id}{file_extension}"
    
    def generate_upload_signature(self, content_type: str, file_extension: str, 
                                 expires_in: int = 3600) -> Dict:
        """生成上传签名 URL"""
        try:
            # 生成对象键名
            object_key = self.generate_object_key(file_extension)
            
            # 生成预签名 URL
            presigned_url = self.s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_key,
                    'ContentType': content_type
                },
                ExpiresIn=expires_in
            )
            
            # 生成下载 URL（用于后续访问）
            download_url = self.generate_download_url(object_key, expires_in=7*24*3600)  # 7天有效期
            
            return {
                "upload_url": presigned_url,
                "download_url": download_url,
                "object_key": object_key,
                "bucket": self.bucket_name,
                "expires_in": expires_in,
                "content_type": content_type
            }
            
        except Exception as e:
            logger.error(f"Failed to generate upload signature: {e}")
            raise
    
    def generate_download_url(self, object_key: str, expires_in: int = 3600) -> str:
        """生成下载签名 URL"""
        try:
            presigned_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_key
                },
                ExpiresIn=expires_in
            )
            return presigned_url
            
        except Exception as e:
            logger.error(f"Failed to generate download URL for {object_key}: {e}")
            raise
    
    def upload_file(self, file_path: str, object_key: str, content_type: str = None) -> str:
        """直接上传文件到对象存储"""
        try:
            # 自动检测内容类型
            if not content_type:
                content_type, _ = mimetypes.guess_type(file_path)
                if not content_type:
                    content_type = 'application/octet-stream'
            
            # 上传文件
            self.s3_client.upload_file(
                file_path,
                self.bucket_name,
                object_key,
                ExtraArgs={'ContentType': content_type}
            )
            
            logger.info(f"Uploaded file: {file_path} -> {object_key}")
            return object_key
            
        except Exception as e:
            logger.error(f"Failed to upload file {file_path}: {e}")
            raise
    
    def download_file(self, object_key: str, local_path: str) -> str:
        """从对象存储下载文件"""
        try:
            self.s3_client.download_file(
                self.bucket_name,
                object_key,
                local_path
            )
            
            logger.info(f"Downloaded file: {object_key} -> {local_path}")
            return local_path
            
        except Exception as e:
            logger.error(f"Failed to download file {object_key}: {e}")
            raise
    
    def delete_file(self, object_key: str) -> bool:
        """删除对象存储中的文件"""
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            
            logger.info(f"Deleted file: {object_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete file {object_key}: {e}")
            return False
    
    def file_exists(self, object_key: str) -> bool:
        """检查文件是否存在"""
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                return False
            else:
                logger.error(f"Error checking file existence {object_key}: {e}")
                raise
    
    def get_file_info(self, object_key: str) -> Optional[Dict]:
        """获取文件信息"""
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            
            return {
                "object_key": object_key,
                "size": response.get('ContentLength', 0),
                "content_type": response.get('ContentType', ''),
                "last_modified": response.get('LastModified'),
                "etag": response.get('ETag', '').strip('"'),
                "metadata": response.get('Metadata', {})
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                return None
            else:
                logger.error(f"Error getting file info {object_key}: {e}")
                raise
    
    def list_files(self, prefix: str = "", max_keys: int = 1000) -> list:
        """列出文件"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            files = []
            for obj in response.get('Contents', []):
                files.append({
                    "object_key": obj['Key'],
                    "size": obj['Size'],
                    "last_modified": obj['LastModified'],
                    "etag": obj['ETag'].strip('"')
                })
            
            return files
            
        except Exception as e:
            logger.error(f"Failed to list files with prefix {prefix}: {e}")
            raise
    
    def generate_multipart_upload(self, object_key: str, content_type: str) -> Dict:
        """生成分片上传"""
        try:
            response = self.s3_client.create_multipart_upload(
                Bucket=self.bucket_name,
                Key=object_key,
                ContentType=content_type
            )
            
            upload_id = response['UploadId']
            
            return {
                "upload_id": upload_id,
                "object_key": object_key,
                "bucket": self.bucket_name
            }
            
        except Exception as e:
            logger.error(f"Failed to create multipart upload: {e}")
            raise
    
    def generate_multipart_upload_urls(self, object_key: str, upload_id: str, 
                                     part_count: int, expires_in: int = 3600) -> list:
        """生成分片上传 URL"""
        try:
            urls = []
            
            for part_number in range(1, part_count + 1):
                presigned_url = self.s3_client.generate_presigned_url(
                    'upload_part',
                    Params={
                        'Bucket': self.bucket_name,
                        'Key': object_key,
                        'UploadId': upload_id,
                        'PartNumber': part_number
                    },
                    ExpiresIn=expires_in
                )
                
                urls.append({
                    "part_number": part_number,
                    "upload_url": presigned_url
                })
            
            return urls
            
        except Exception as e:
            logger.error(f"Failed to generate multipart upload URLs: {e}")
            raise
    
    def complete_multipart_upload(self, object_key: str, upload_id: str, parts: list) -> str:
        """完成分片上传"""
        try:
            response = self.s3_client.complete_multipart_upload(
                Bucket=self.bucket_name,
                Key=object_key,
                UploadId=upload_id,
                MultipartUpload={'Parts': parts}
            )
            
            logger.info(f"Completed multipart upload: {object_key}")
            return response['ETag'].strip('"')
            
        except Exception as e:
            logger.error(f"Failed to complete multipart upload: {e}")
            raise

# 全局存储服务实例
storage_service = StorageService()
