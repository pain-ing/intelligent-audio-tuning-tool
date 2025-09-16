"""
统一配置管理模块
"""
import os
from typing import Optional, Dict, Any
try:
    from pydantic_settings import BaseSettings
    from pydantic import Field
except ImportError:
    try:
        # 兼容旧版本pydantic
        from pydantic import BaseSettings, Field
    except ImportError:
        # 最终兜底 - 创建最小化BaseSettings
        from pydantic import BaseModel, Field
        class BaseSettings(BaseModel):
            class Config:
                env_file = ".env"
                env_file_encoding = "utf-8"
from enum import Enum


class AppMode(str, Enum):
    """应用模式枚举"""
    CLOUD = "cloud"
    DESKTOP = "desktop"


class StorageMode(str, Enum):
    """存储模式枚举"""
    S3 = "s3"
    MINIO = "minio"
    LOCAL = "local"


class CacheMode(str, Enum):
    """缓存模式枚举"""
    REDIS = "redis"
    LOCAL = "local"
    DISABLED = "disabled"


class BaseConfig(BaseSettings):
    """基础配置类"""
    model_config = {
        "extra": "ignore",  # 忽略额外字段
        "env_file": ".env",
        "case_sensitive": False
    }
    
    # 应用基础配置
    app_name: str = Field(default="Audio Tuner", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    app_mode: AppMode = Field(default=AppMode.CLOUD, env="APP_MODE")
    debug: bool = Field(default=False, env="DEBUG")
    
    # 服务器配置
    host: str = Field(default="127.0.0.1", env="HOST")
    port: int = Field(default=8080, env="PORT")
    
    # 数据库配置
    database_url: Optional[str] = Field(default=None, env="DATABASE_URL")
    
    # 存储配置
    storage_mode: StorageMode = Field(default=StorageMode.LOCAL, env="STORAGE_MODE")
    storage_bucket: str = Field(default="audio-tuner", env="STORAGE_BUCKET")
    storage_endpoint: Optional[str] = Field(default=None, env="STORAGE_ENDPOINT")
    storage_access_key: Optional[str] = Field(default=None, env="STORAGE_ACCESS_KEY")
    storage_secret_key: Optional[str] = Field(default=None, env="STORAGE_SECRET_KEY")
    
    # 缓存配置
    cache_mode: CacheMode = Field(default=CacheMode.LOCAL, env="CACHE_MODE")
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
    
    # 任务队列配置
    celery_broker_url: Optional[str] = Field(default=None, env="CELERY_BROKER_URL")
    celery_result_backend: Optional[str] = Field(default=None, env="CELERY_RESULT_BACKEND")
    
    # 音频处理配置
    max_file_size: int = Field(default=100 * 1024 * 1024, env="MAX_FILE_SIZE")  # 100MB
    supported_formats: list = Field(default=["wav", "mp3", "flac", "m4a"], env="SUPPORTED_FORMATS")
    
    # 性能配置
    worker_concurrency: int = Field(default=4, env="WORKER_CONCURRENCY")
    chunk_size: int = Field(default=1024, env="CHUNK_SIZE")
    



class CloudConfig(BaseConfig):
    """云端配置"""
    app_mode: AppMode = AppMode.CLOUD
    storage_mode: StorageMode = StorageMode.MINIO
    cache_mode: CacheMode = CacheMode.REDIS


class DesktopConfig(BaseConfig):
    """桌面配置"""
    app_mode: AppMode = AppMode.DESKTOP
    storage_mode: StorageMode = StorageMode.LOCAL
    cache_mode: CacheMode = CacheMode.LOCAL
    
    # 桌面特有配置
    data_dir: str = Field(default="", env="DATA_DIR")
    resources_path: str = Field(default="", env="RESOURCES_PATH")


def get_config() -> BaseConfig:
    """获取配置实例"""
    app_mode = os.getenv("APP_MODE", "cloud").lower()

    if app_mode == "desktop":
        cfg = DesktopConfig()
        # 若未显式设置数据库，则为桌面模式自动设置本地 SQLite
        if not cfg.database_url:
            data_dir = cfg.data_dir or os.path.join(os.path.expanduser("~"), ".audio_tuner")
            try:
                os.makedirs(data_dir, exist_ok=True)
            except Exception:
                # 在极端情况下，fallback 到临时目录
                data_dir = os.path.join(os.getcwd(), ".audio_tuner")
                os.makedirs(data_dir, exist_ok=True)
            sqlite_db_path = os.path.join(data_dir, "app.db").replace("\\", "/")
            sqlite_uri = f"sqlite:///{sqlite_db_path}"
            try:
                object.__setattr__(cfg, "database_url", sqlite_uri)
            except Exception:
                # 如果设置失败，不抛出致命错误，仅记录
                pass
        return cfg
    else:
        return CloudConfig()


# 全局配置实例
config = get_config()
