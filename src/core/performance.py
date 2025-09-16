"""
性能优化模块
"""
import time
import asyncio
import logging
from typing import Dict, Any, Optional, Callable, List
from functools import wraps
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
import psutil
import threading

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """性能指标"""
    operation: str
    start_time: float
    end_time: float
    duration: float
    memory_before: float
    memory_after: float
    memory_peak: float
    cpu_percent: float
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation": self.operation,
            "duration_ms": round(self.duration * 1000, 2),
            "memory_before_mb": round(self.memory_before / 1024 / 1024, 2),
            "memory_after_mb": round(self.memory_after / 1024 / 1024, 2),
            "memory_peak_mb": round(self.memory_peak / 1024 / 1024, 2),
            "cpu_percent": round(self.cpu_percent, 2),
            "success": self.success,
            "error": self.error,
            "metadata": self.metadata
        }


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []
        self.active_operations: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    @asynccontextmanager
    async def monitor_operation(self, operation_name: str, metadata: Optional[Dict[str, Any]] = None):
        """监控操作性能"""
        operation_id = f"{operation_name}_{int(time.time() * 1000)}"
        
        # 记录开始状态
        start_time = time.perf_counter()
        process = psutil.Process()
        memory_before = process.memory_info().rss
        
        with self._lock:
            self.active_operations[operation_id] = {
                "start_time": start_time,
                "memory_before": memory_before,
                "peak_memory": memory_before
            }
        
        # 启动内存监控
        monitor_task = asyncio.create_task(self._monitor_memory(operation_id))
        
        try:
            yield operation_id
            success = True
            error = None
        except Exception as e:
            success = False
            error = str(e)
            raise
        finally:
            # 停止监控
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass
            
            # 记录结束状态
            end_time = time.perf_counter()
            memory_after = process.memory_info().rss
            cpu_percent = process.cpu_percent()
            
            with self._lock:
                op_data = self.active_operations.pop(operation_id, {})
                peak_memory = op_data.get("peak_memory", memory_after)
            
            # 创建性能指标
            metrics = PerformanceMetrics(
                operation=operation_name,
                start_time=start_time,
                end_time=end_time,
                duration=end_time - start_time,
                memory_before=memory_before,
                memory_after=memory_after,
                memory_peak=peak_memory,
                cpu_percent=cpu_percent,
                success=success,
                error=error,
                metadata=metadata or {}
            )
            
            self.metrics.append(metrics)
            
            # 记录日志
            if success:
                logger.info(f"Operation {operation_name} completed in {metrics.duration:.3f}s")
            else:
                logger.error(f"Operation {operation_name} failed after {metrics.duration:.3f}s: {error}")
    
    async def _monitor_memory(self, operation_id: str):
        """监控内存使用峰值"""
        process = psutil.Process()
        
        try:
            while True:
                current_memory = process.memory_info().rss
                
                with self._lock:
                    if operation_id in self.active_operations:
                        op_data = self.active_operations[operation_id]
                        if current_memory > op_data["peak_memory"]:
                            op_data["peak_memory"] = current_memory
                
                await asyncio.sleep(0.1)  # 每100ms检查一次
        except asyncio.CancelledError:
            pass
    
    def get_metrics(self, operation: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取性能指标"""
        if operation:
            filtered_metrics = [m for m in self.metrics if m.operation == operation]
        else:
            filtered_metrics = self.metrics
        
        return [m.to_dict() for m in filtered_metrics]
    
    def get_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        if not self.metrics:
            return {"total_operations": 0}
        
        total_operations = len(self.metrics)
        successful_operations = sum(1 for m in self.metrics if m.success)
        failed_operations = total_operations - successful_operations
        
        durations = [m.duration for m in self.metrics if m.success]
        if durations:
            avg_duration = sum(durations) / len(durations)
            min_duration = min(durations)
            max_duration = max(durations)
        else:
            avg_duration = min_duration = max_duration = 0
        
        memory_usage = [m.memory_peak - m.memory_before for m in self.metrics if m.success]
        if memory_usage:
            avg_memory_usage = sum(memory_usage) / len(memory_usage)
            max_memory_usage = max(memory_usage)
        else:
            avg_memory_usage = max_memory_usage = 0
        
        return {
            "total_operations": total_operations,
            "successful_operations": successful_operations,
            "failed_operations": failed_operations,
            "success_rate": successful_operations / total_operations if total_operations > 0 else 0,
            "avg_duration_ms": round(avg_duration * 1000, 2),
            "min_duration_ms": round(min_duration * 1000, 2),
            "max_duration_ms": round(max_duration * 1000, 2),
            "avg_memory_usage_mb": round(avg_memory_usage / 1024 / 1024, 2),
            "max_memory_usage_mb": round(max_memory_usage / 1024 / 1024, 2)
        }
    
    def clear_metrics(self):
        """清空指标"""
        self.metrics.clear()


# 全局性能监控器
performance_monitor = PerformanceMonitor()


def monitor_performance(operation_name: str, metadata: Optional[Dict[str, Any]] = None):
    """性能监控装饰器"""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                async with performance_monitor.monitor_operation(operation_name, metadata):
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # 对于同步函数，创建一个异步上下文
                async def _run():
                    async with performance_monitor.monitor_operation(operation_name, metadata):
                        return func(*args, **kwargs)
                
                # 如果在异步环境中，直接运行
                try:
                    loop = asyncio.get_running_loop()
                    # 在当前事件循环中运行
                    task = asyncio.create_task(_run())
                    return asyncio.run_coroutine_threadsafe(task, loop).result()
                except RuntimeError:
                    # 如果没有运行的事件循环，创建新的
                    return asyncio.run(_run())
            
            return sync_wrapper
    return decorator


class ResourcePool:
    """资源池管理"""
    
    def __init__(self, max_size: int = 10):
        self.max_size = max_size
        self.pool: List[Any] = []
        self.in_use: set = set()
        self._lock = asyncio.Lock()
    
    async def acquire(self, factory: Callable = None) -> Any:
        """获取资源"""
        async with self._lock:
            if self.pool:
                resource = self.pool.pop()
                self.in_use.add(id(resource))
                return resource
            elif len(self.in_use) < self.max_size and factory:
                resource = factory()
                self.in_use.add(id(resource))
                return resource
            else:
                raise RuntimeError("Resource pool exhausted")
    
    async def release(self, resource: Any):
        """释放资源"""
        async with self._lock:
            resource_id = id(resource)
            if resource_id in self.in_use:
                self.in_use.remove(resource_id)
                self.pool.append(resource)
    
    @asynccontextmanager
    async def get_resource(self, factory: Callable = None):
        """获取资源的上下文管理器"""
        resource = await self.acquire(factory)
        try:
            yield resource
        finally:
            await self.release(resource)


class BatchProcessor:
    """批处理器"""
    
    def __init__(self, batch_size: int = 10, max_wait_time: float = 1.0):
        self.batch_size = batch_size
        self.max_wait_time = max_wait_time
        self.pending_items: List[Any] = []
        self.pending_futures: List[asyncio.Future] = []
        self._lock = asyncio.Lock()
        self._process_task: Optional[asyncio.Task] = None
    
    async def add_item(self, item: Any) -> Any:
        """添加项目到批处理队列"""
        future = asyncio.Future()
        
        async with self._lock:
            self.pending_items.append(item)
            self.pending_futures.append(future)
            
            # 如果达到批处理大小，立即处理
            if len(self.pending_items) >= self.batch_size:
                if self._process_task:
                    self._process_task.cancel()
                self._process_task = asyncio.create_task(self._process_batch())
            elif not self._process_task:
                # 启动定时处理
                self._process_task = asyncio.create_task(self._wait_and_process())
        
        return await future
    
    async def _wait_and_process(self):
        """等待并处理批次"""
        await asyncio.sleep(self.max_wait_time)
        await self._process_batch()
    
    async def _process_batch(self):
        """处理当前批次"""
        async with self._lock:
            if not self.pending_items:
                return
            
            items = self.pending_items.copy()
            futures = self.pending_futures.copy()
            
            self.pending_items.clear()
            self.pending_futures.clear()
            self._process_task = None
        
        try:
            # 这里应该实现具体的批处理逻辑
            results = await self._process_items_batch(items)
            
            # 设置结果
            for future, result in zip(futures, results):
                if not future.done():
                    future.set_result(result)
        except Exception as e:
            # 设置异常
            for future in futures:
                if not future.done():
                    future.set_exception(e)
    
    async def _process_items_batch(self, items: List[Any]) -> List[Any]:
        """处理项目批次 - 子类应该重写此方法"""
        # 默认实现：返回原始项目
        return items


# 便捷函数
async def get_system_metrics() -> Dict[str, Any]:
    """获取系统指标"""
    process = psutil.Process()
    
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory_percent": psutil.virtual_memory().percent,
        "memory_available_mb": psutil.virtual_memory().available / 1024 / 1024,
        "disk_usage_percent": psutil.disk_usage('/').percent,
        "process_memory_mb": process.memory_info().rss / 1024 / 1024,
        "process_cpu_percent": process.cpu_percent(),
        "thread_count": process.num_threads()
    }
