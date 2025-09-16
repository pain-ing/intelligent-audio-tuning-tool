"""
依赖注入容器
"""
from typing import Dict, Any, Type, TypeVar, Callable, Optional
import inspect
import os
from functools import wraps

from src.core.config import config, AppMode, StorageMode, CacheMode
from src.services.base import (
    StorageServiceInterface,
    CacheServiceInterface,
    AudioProcessorInterface
)

# 导入优化的容器
try:
    from .container_optimized import (
        get_optimized_container,
        get_service as optimized_get_service,
        get_storage_service as optimized_get_storage_service,
        get_cache_service as optimized_get_cache_service,
        get_audio_service as optimized_get_audio_service,
        service_scope,
        ServiceScope
    )
    OPTIMIZED_CONTAINER_AVAILABLE = True
except ImportError:
    OPTIMIZED_CONTAINER_AVAILABLE = False

T = TypeVar('T')

# 容器模式选择
CONTAINER_MODE = os.getenv("CONTAINER_MODE", "optimized" if OPTIMIZED_CONTAINER_AVAILABLE else "traditional").lower()


class DIContainer:
    """依赖注入容器"""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}
        self._setup_default_services()
    
    def _setup_default_services(self):
        """设置默认服务"""
        # 注册配置
        self.register_singleton("config", config)
        
        # 注册服务工厂
        self.register_factory("storage_service", self._create_storage_service)
        self.register_factory("cache_service", self._create_cache_service)
        self.register_factory("audio_service", self._create_audio_service)
    
    def register_singleton(self, name: str, instance: Any):
        """注册单例服务"""
        self._singletons[name] = instance
    
    def register_factory(self, name: str, factory: Callable):
        """注册工厂函数"""
        self._factories[name] = factory
    
    def register_service(self, name: str, service_class: Type[T]) -> Type[T]:
        """注册服务类"""
        self._services[name] = service_class
        return service_class
    
    def get(self, name: str) -> Any:
        """获取服务实例"""
        # 检查单例
        if name in self._singletons:
            return self._singletons[name]
        
        # 检查工厂
        if name in self._factories:
            instance = self._factories[name]()
            # 如果是单例模式，缓存实例
            if hasattr(instance, '_singleton') and instance._singleton:
                self._singletons[name] = instance
            return instance
        
        # 检查服务类
        if name in self._services:
            service_class = self._services[name]
            instance = self._create_instance(service_class)
            return instance
        
        raise ValueError(f"Service '{name}' not found")
    
    def _create_instance(self, service_class: Type[T]) -> T:
        """创建服务实例，自动注入依赖"""
        # 获取构造函数签名
        sig = inspect.signature(service_class.__init__)
        kwargs = {}
        
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            
            # 尝试从容器获取依赖
            try:
                kwargs[param_name] = self.get(param_name)
            except ValueError:
                # 如果有默认值，使用默认值
                if param.default != inspect.Parameter.empty:
                    kwargs[param_name] = param.default
                else:
                    # 尝试根据类型注解获取服务
                    if param.annotation != inspect.Parameter.empty:
                        service_name = self._get_service_name_by_type(param.annotation)
                        if service_name:
                            kwargs[param_name] = self.get(service_name)
        
        return service_class(**kwargs)
    
    def _get_service_name_by_type(self, service_type: Type) -> Optional[str]:
        """根据类型获取服务名称"""
        type_mapping = {
            StorageServiceInterface: "storage_service",
            CacheServiceInterface: "cache_service",
            AudioProcessorInterface: "audio_service"
        }
        return type_mapping.get(service_type)
    
    def _create_storage_service(self) -> StorageServiceInterface:
        """创建存储服务"""
        if config.storage_mode == StorageMode.LOCAL:
            from src.services.storage_service import LocalStorageService
            return LocalStorageService()
        elif config.storage_mode == StorageMode.MINIO:
            from src.services.storage_service import MinIOStorageService
            return MinIOStorageService()
        else:
            raise ValueError(f"Unsupported storage mode: {config.storage_mode}")
    
    def _create_cache_service(self) -> CacheServiceInterface:
        """创建缓存服务"""
        if config.cache_mode == CacheMode.LOCAL:
            from src.services.cache_service import LocalCacheService
            return LocalCacheService()
        elif config.cache_mode == CacheMode.REDIS:
            from src.services.cache_service import RedisCacheService
            return RedisCacheService()
        elif config.cache_mode == CacheMode.DISABLED:
            from src.services.cache_service import DisabledCacheService
            return DisabledCacheService()
        else:
            raise ValueError(f"Unsupported cache mode: {config.cache_mode}")
    
    def _create_audio_service(self) -> AudioProcessorInterface:
        """创建音频服务"""
        from src.services.audio_service import AudioService
        return AudioService()


# 全局容器实例
container = DIContainer()


# 装饰器
def inject(*dependencies):
    """依赖注入装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 注入依赖
            for dep_name in dependencies:
                if dep_name not in kwargs:
                    kwargs[dep_name] = container.get(dep_name)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def service(name: Optional[str] = None, singleton: bool = False):
    """服务注册装饰器"""
    def decorator(cls):
        service_name = name or cls.__name__.lower().replace('service', '_service')
        
        if singleton:
            cls._singleton = True
        
        container.register_service(service_name, cls)
        return cls
    return decorator


# 便捷函数
def get_service(name: str) -> Any:
    """获取服务实例"""
    return container.get(name)


def get_storage_service() -> StorageServiceInterface:
    """获取存储服务（自动选择容器后端）"""
    if CONTAINER_MODE == "optimized" and OPTIMIZED_CONTAINER_AVAILABLE:
        return optimized_get_storage_service()
    return container.get("storage_service")


def get_cache_service() -> CacheServiceInterface:
    """获取缓存服务（自动选择容器后端）"""
    if CONTAINER_MODE == "optimized" and OPTIMIZED_CONTAINER_AVAILABLE:
        return optimized_get_cache_service()
    return container.get("cache_service")


def get_audio_service() -> AudioProcessorInterface:
    """获取音频服务（自动选择容器后端）"""
    if CONTAINER_MODE == "optimized" and OPTIMIZED_CONTAINER_AVAILABLE:
        return optimized_get_audio_service()
    return container.get("audio_service")


def get_service(name: str) -> Any:
    """获取服务实例（自动选择容器后端）"""
    if CONTAINER_MODE == "optimized" and OPTIMIZED_CONTAINER_AVAILABLE:
        return optimized_get_service(name)
    return container.get(name)


def get_container_stats() -> Dict[str, Any]:
    """获取容器统计信息"""
    if CONTAINER_MODE == "optimized" and OPTIMIZED_CONTAINER_AVAILABLE:
        optimized_container = get_optimized_container()
        return optimized_container.get_stats()

    # 传统容器的简单统计
    return {
        "backend": "traditional",
        "singletons_count": len(container._singletons),
        "services_count": len(container._services),
        "factories_count": len(container._factories)
    }


# 上下文管理器
class ServiceScope:
    """服务作用域上下文管理器"""
    
    def __init__(self, **overrides):
        self.overrides = overrides
        self.original_services = {}
    
    def __enter__(self):
        # 保存原始服务
        for name, service in self.overrides.items():
            if name in container._singletons:
                self.original_services[name] = container._singletons[name]
            container.register_singleton(name, service)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # 恢复原始服务
        for name in self.overrides:
            if name in self.original_services:
                container._singletons[name] = self.original_services[name]
            else:
                container._singletons.pop(name, None)
