"""
内存优化的依赖注入容器
实现作用域控制、生命周期管理和及时释放
"""

from typing import Dict, Any, Type, TypeVar, Callable, Optional, Set, List
import inspect
import threading
import weakref
import gc
import time
import logging
from functools import wraps
from enum import Enum
from contextlib import contextmanager
from dataclasses import dataclass

from src.core.config import config, AppMode, StorageMode, CacheMode
from src.services.base import (
    StorageServiceInterface,
    CacheServiceInterface,
    AudioProcessorInterface
)

logger = logging.getLogger(__name__)

T = TypeVar('T')

class ServiceScope(Enum):
    """服务作用域"""
    SINGLETON = "singleton"      # 全局单例
    SCOPED = "scoped"           # 作用域内单例
    TRANSIENT = "transient"     # 每次创建新实例
    WEAK_SINGLETON = "weak_singleton"  # 弱引用单例

@dataclass
class ServiceRegistration:
    """服务注册信息"""
    name: str
    service_class: Type
    factory: Optional[Callable]
    scope: ServiceScope
    created_at: float
    last_accessed: float
    access_count: int
    dependencies: Set[str]

class MemoryOptimizedDIContainer:
    """内存优化的依赖注入容器"""
    
    def __init__(self, enable_cleanup: bool = True, cleanup_interval: float = 300.0):
        """
        初始化容器
        
        Args:
            enable_cleanup: 是否启用自动清理
            cleanup_interval: 清理间隔（秒）
        """
        # 服务注册表
        self._registrations: Dict[str, ServiceRegistration] = {}
        
        # 不同作用域的实例存储
        self._singletons: Dict[str, Any] = {}
        self._weak_singletons: Dict[str, weakref.ref] = {}
        self._scoped_instances: Dict[str, Dict[str, Any]] = {}  # scope_id -> {service_name: instance}
        
        # 作用域管理
        self._current_scope_id: Optional[str] = None
        self._scope_stack: List[str] = []
        
        # 线程安全
        self._lock = threading.RLock()
        
        # 清理管理
        self.enable_cleanup = enable_cleanup
        self.cleanup_interval = cleanup_interval
        self._cleanup_thread = None
        self._stop_cleanup = threading.Event()
        
        # 统计信息
        self._creation_count = 0
        self._cleanup_count = 0
        
        # 设置默认服务
        self._setup_default_services()
        
        # 启动清理线程
        if enable_cleanup:
            self._start_cleanup_thread()
        
        logger.info("内存优化依赖注入容器初始化完成")
    
    def _setup_default_services(self):
        """设置默认服务"""
        # 注册配置为单例
        self.register_singleton("config", config)
        
        # 注册服务工厂
        self.register_factory("storage_service", self._create_storage_service, ServiceScope.WEAK_SINGLETON)
        self.register_factory("cache_service", self._create_cache_service, ServiceScope.WEAK_SINGLETON)
        self.register_factory("audio_service", self._create_audio_service, ServiceScope.SCOPED)
    
    def _start_cleanup_thread(self):
        """启动清理线程"""
        if self._cleanup_thread is None or not self._cleanup_thread.is_alive():
            self._stop_cleanup.clear()
            self._cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
            self._cleanup_thread.start()
    
    def _cleanup_worker(self):
        """清理工作线程"""
        while not self._stop_cleanup.wait(self.cleanup_interval):
            try:
                self._periodic_cleanup()
            except Exception as e:
                logger.error(f"依赖注入容器清理失败: {e}")
    
    def _periodic_cleanup(self):
        """定期清理"""
        with self._lock:
            current_time = time.time()
            
            # 清理弱引用单例中的死引用
            dead_refs = []
            for name, weak_ref in self._weak_singletons.items():
                if weak_ref() is None:
                    dead_refs.append(name)
            
            for name in dead_refs:
                del self._weak_singletons[name]
                self._cleanup_count += 1
            
            # 清理长时间未访问的作用域实例
            inactive_scopes = []
            for scope_id, instances in self._scoped_instances.items():
                if scope_id != self._current_scope_id:
                    # 检查是否有注册信息表明长时间未访问
                    scope_inactive = True
                    for service_name in instances.keys():
                        if service_name in self._registrations:
                            reg = self._registrations[service_name]
                            if current_time - reg.last_accessed < 3600:  # 1小时内访问过
                                scope_inactive = False
                                break
                    
                    if scope_inactive:
                        inactive_scopes.append(scope_id)
            
            for scope_id in inactive_scopes:
                instances = self._scoped_instances.pop(scope_id, {})
                self._cleanup_count += len(instances)
                del instances
            
            # 强制垃圾回收
            if dead_refs or inactive_scopes:
                gc.collect()
                logger.debug(f"清理完成: 移除了 {len(dead_refs)} 个死引用, {len(inactive_scopes)} 个非活跃作用域")
    
    def register_singleton(self, name: str, instance: Any):
        """注册单例服务"""
        with self._lock:
            self._singletons[name] = instance
            self._registrations[name] = ServiceRegistration(
                name=name,
                service_class=type(instance),
                factory=None,
                scope=ServiceScope.SINGLETON,
                created_at=time.time(),
                last_accessed=time.time(),
                access_count=0,
                dependencies=set()
            )
    
    def register_factory(self, name: str, factory: Callable, scope: ServiceScope = ServiceScope.TRANSIENT):
        """注册工厂函数"""
        with self._lock:
            self._registrations[name] = ServiceRegistration(
                name=name,
                service_class=None,
                factory=factory,
                scope=scope,
                created_at=time.time(),
                last_accessed=time.time(),
                access_count=0,
                dependencies=self._analyze_dependencies(factory)
            )
    
    def register_service(self, name: str, service_class: Type[T], scope: ServiceScope = ServiceScope.TRANSIENT) -> Type[T]:
        """注册服务类"""
        with self._lock:
            self._registrations[name] = ServiceRegistration(
                name=name,
                service_class=service_class,
                factory=None,
                scope=scope,
                created_at=time.time(),
                last_accessed=time.time(),
                access_count=0,
                dependencies=self._analyze_dependencies(service_class.__init__)
            )
            return service_class
    
    def _analyze_dependencies(self, func: Callable) -> Set[str]:
        """分析函数的依赖"""
        try:
            sig = inspect.signature(func)
            dependencies = set()
            
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                
                # 简单的依赖分析，可以根据需要扩展
                if param_name.endswith('_service'):
                    dependencies.add(param_name)
            
            return dependencies
        except Exception:
            return set()
    
    def get(self, name: str) -> Any:
        """获取服务实例"""
        with self._lock:
            if name not in self._registrations:
                raise ValueError(f"Service '{name}' not registered")
            
            registration = self._registrations[name]
            registration.last_accessed = time.time()
            registration.access_count += 1
            
            # 根据作用域获取实例
            if registration.scope == ServiceScope.SINGLETON:
                return self._get_singleton(name, registration)
            elif registration.scope == ServiceScope.WEAK_SINGLETON:
                return self._get_weak_singleton(name, registration)
            elif registration.scope == ServiceScope.SCOPED:
                return self._get_scoped(name, registration)
            else:  # TRANSIENT
                return self._create_instance(name, registration)
    
    def _get_singleton(self, name: str, registration: ServiceRegistration) -> Any:
        """获取单例实例"""
        if name not in self._singletons:
            self._singletons[name] = self._create_instance(name, registration)
        return self._singletons[name]
    
    def _get_weak_singleton(self, name: str, registration: ServiceRegistration) -> Any:
        """获取弱引用单例实例"""
        if name in self._weak_singletons:
            instance = self._weak_singletons[name]()
            if instance is not None:
                return instance
        
        # 创建新实例并存储弱引用
        instance = self._create_instance(name, registration)
        self._weak_singletons[name] = weakref.ref(instance)
        return instance
    
    def _get_scoped(self, name: str, registration: ServiceRegistration) -> Any:
        """获取作用域实例"""
        scope_id = self._current_scope_id or "default"
        
        if scope_id not in self._scoped_instances:
            self._scoped_instances[scope_id] = {}
        
        if name not in self._scoped_instances[scope_id]:
            self._scoped_instances[scope_id][name] = self._create_instance(name, registration)
        
        return self._scoped_instances[scope_id][name]
    
    def _create_instance(self, name: str, registration: ServiceRegistration) -> Any:
        """创建服务实例"""
        try:
            if registration.factory:
                instance = registration.factory()
            elif registration.service_class:
                instance = registration.service_class()
            else:
                raise ValueError(f"No factory or service class for '{name}'")
            
            self._creation_count += 1
            logger.debug(f"创建服务实例: {name}")
            return instance
            
        except Exception as e:
            logger.error(f"创建服务实例失败 '{name}': {e}")
            raise
    
    @contextmanager
    def scope(self, scope_id: str = None):
        """作用域上下文管理器"""
        if scope_id is None:
            scope_id = f"scope_{int(time.time() * 1000)}"
        
        with self._lock:
            # 保存当前作用域
            previous_scope = self._current_scope_id
            self._scope_stack.append(previous_scope)
            
            # 设置新作用域
            self._current_scope_id = scope_id
            
            try:
                yield scope_id
            finally:
                # 恢复之前的作用域
                self._current_scope_id = self._scope_stack.pop()
                
                # 清理当前作用域的实例
                if scope_id in self._scoped_instances:
                    instances = self._scoped_instances.pop(scope_id)
                    self._cleanup_count += len(instances)
                    del instances
                    gc.collect()
    
    def clear_scope(self, scope_id: str):
        """清理指定作用域"""
        with self._lock:
            if scope_id in self._scoped_instances:
                instances = self._scoped_instances.pop(scope_id)
                self._cleanup_count += len(instances)
                del instances
                gc.collect()
                logger.debug(f"清理作用域: {scope_id}")
    
    def clear_all_scopes(self):
        """清理所有作用域"""
        with self._lock:
            total_instances = sum(len(instances) for instances in self._scoped_instances.values())
            self._scoped_instances.clear()
            self._cleanup_count += total_instances
            gc.collect()
            logger.info(f"清理所有作用域: {total_instances} 个实例")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取容器统计信息"""
        with self._lock:
            return {
                "registrations_count": len(self._registrations),
                "singletons_count": len(self._singletons),
                "weak_singletons_count": len(self._weak_singletons),
                "active_scopes_count": len(self._scoped_instances),
                "total_scoped_instances": sum(len(instances) for instances in self._scoped_instances.values()),
                "creation_count": self._creation_count,
                "cleanup_count": self._cleanup_count,
                "current_scope_id": self._current_scope_id
            }
    
    def shutdown(self):
        """关闭容器"""
        # 停止清理线程
        if self._cleanup_thread:
            self._stop_cleanup.set()
            self._cleanup_thread.join(timeout=5.0)
        
        # 清理所有实例
        with self._lock:
            self._singletons.clear()
            self._weak_singletons.clear()
            self._scoped_instances.clear()
            
        gc.collect()
        logger.info("依赖注入容器已关闭")
    
    # 工厂方法（与原容器兼容）
    def _create_storage_service(self):
        """创建存储服务"""
        from src.services.storage_service import get_storage_service
        return get_storage_service()
    
    def _create_cache_service(self):
        """创建缓存服务"""
        from src.services.cache_service import get_cache_service
        return get_cache_service()
    
    def _create_audio_service(self):
        """创建音频服务"""
        from src.services.audio_service import AudioService
        return AudioService()

# 全局优化容器实例
_optimized_container = None
_container_lock = threading.Lock()

def get_optimized_container() -> MemoryOptimizedDIContainer:
    """获取全局优化容器实例"""
    global _optimized_container
    
    if _optimized_container is None:
        with _container_lock:
            if _optimized_container is None:
                _optimized_container = MemoryOptimizedDIContainer()
    
    return _optimized_container

# 兼容性函数
def get_service(name: str) -> Any:
    """获取服务实例（兼容性函数）"""
    container = get_optimized_container()
    return container.get(name)

def get_storage_service() -> StorageServiceInterface:
    """获取存储服务"""
    return get_service("storage_service")

def get_cache_service() -> CacheServiceInterface:
    """获取缓存服务"""
    return get_service("cache_service")

def get_audio_service() -> AudioProcessorInterface:
    """获取音频服务"""
    return get_service("audio_service")

# 装饰器
def inject(*dependencies):
    """依赖注入装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            container = get_optimized_container()
            # 注入依赖
            for dep_name in dependencies:
                if dep_name not in kwargs:
                    kwargs[dep_name] = container.get(dep_name)
            return func(*args, **kwargs)
        return wrapper
    return decorator

def service(name: Optional[str] = None, scope: ServiceScope = ServiceScope.TRANSIENT):
    """服务注册装饰器"""
    def decorator(cls):
        service_name = name or cls.__name__.lower().replace('service', '_service')
        container = get_optimized_container()
        container.register_service(service_name, cls, scope)
        return cls
    return decorator

# 作用域上下文管理器
@contextmanager
def service_scope(scope_id: str = None):
    """服务作用域上下文管理器"""
    container = get_optimized_container()
    with container.scope(scope_id) as scope:
        yield scope
