"""
基础服务类
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging

from src.core.config import config
from src.core.exceptions import AudioTunerException


class BaseService(ABC):
    """基础服务类"""
    
    def __init__(self):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _handle_error(self, error: Exception, context: str = "") -> None:
        """统一错误处理"""
        if isinstance(error, AudioTunerException):
            self.logger.error(f"{context}: {error.message}", extra={"detail": error.detail})
            raise error
        else:
            self.logger.error(f"{context}: {str(error)}", exc_info=True)
            raise AudioTunerException(
                message=f"Internal error in {context}",
                detail={"original_error": str(error)}
            )


class StorageServiceInterface(ABC):
    """存储服务接口"""
    
    @abstractmethod
    async def upload_file(self, file_path: str, object_key: str) -> str:
        """上传文件"""
        pass
    
    @abstractmethod
    async def download_file(self, object_key: str, file_path: str) -> None:
        """下载文件"""
        pass
    
    @abstractmethod
    async def delete_file(self, object_key: str) -> None:
        """删除文件"""
        pass
    
    @abstractmethod
    async def get_download_url(self, object_key: str, expires_in: int = 3600) -> str:
        """获取下载URL"""
        pass


class CacheServiceInterface(ABC):
    """缓存服务接口"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """设置缓存"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> None:
        """删除缓存"""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        pass


class TaskQueueInterface(ABC):
    """任务队列接口"""
    
    @abstractmethod
    async def enqueue(self, task_name: str, *args, **kwargs) -> str:
        """入队任务"""
        pass
    
    @abstractmethod
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        pass
    
    @abstractmethod
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        pass


class AudioProcessorInterface(ABC):
    """音频处理器接口"""
    
    @abstractmethod
    async def analyze_features(self, file_path: str) -> Dict[str, Any]:
        """分析音频特征"""
        pass
    
    @abstractmethod
    async def invert_parameters(
        self,
        ref_features: Dict[str, Any],
        tgt_features: Dict[str, Any],
        mode: str
    ) -> Dict[str, Any]:
        """参数反演"""
        pass
    
    @abstractmethod
    async def render_audio(
        self,
        input_path: str,
        output_path: str,
        style_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """音频渲染"""
        pass
