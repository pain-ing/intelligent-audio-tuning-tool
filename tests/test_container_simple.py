#!/usr/bin/env python3
"""
依赖注入容器优化简化测试
验证容器生命周期管理和内存优化效果
"""

import sys
import os
import gc
import time
import weakref
from pathlib import Path
from typing import Dict, List, Tuple, Any, Type, TypeVar, Callable, Optional, Set
import threading
from enum import Enum
from contextlib import contextmanager
from dataclasses import dataclass
import logging

# 导入测试模块
from test_memory_optimization import MemoryProfiler, memory_profiler

logger = logging.getLogger(__name__)

# 简化的容器实现用于测试
class ServiceScope(Enum):
    """服务作用域"""
    SINGLETON = "singleton"
    SCOPED = "scoped"
    TRANSIENT = "transient"
    WEAK_SINGLETON = "weak_singleton"

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

class SimpleOptimizedContainer:
    """简化的优化容器"""
    
    def __init__(self):
        self._registrations: Dict[str, ServiceRegistration] = {}
        self._singletons: Dict[str, Any] = {}
        self._weak_singletons: Dict[str, weakref.ref] = {}
        self._scoped_instances: Dict[str, Dict[str, Any]] = {}
        self._current_scope_id: Optional[str] = None
        self._lock = threading.RLock()
        self._creation_count = 0
        self._cleanup_count = 0
    
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
                access_count=0
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
                access_count=0
            )
    
    def get(self, name: str) -> Any:
        """获取服务实例"""
        with self._lock:
            if name not in self._registrations:
                raise ValueError(f"Service '{name}' not registered")
            
            registration = self._registrations[name]
            registration.last_accessed = time.time()
            registration.access_count += 1
            
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
        if registration.factory:
            instance = registration.factory()
        else:
            raise ValueError(f"No factory for '{name}'")
        
        self._creation_count += 1
        return instance
    
    @contextmanager
    def scope(self, scope_id: str = None):
        """作用域上下文管理器"""
        if scope_id is None:
            scope_id = f"scope_{int(time.time() * 1000)}"
        
        with self._lock:
            previous_scope = self._current_scope_id
            self._current_scope_id = scope_id
            
            try:
                yield scope_id
            finally:
                self._current_scope_id = previous_scope
                
                if scope_id in self._scoped_instances:
                    instances = self._scoped_instances.pop(scope_id)
                    self._cleanup_count += len(instances)
                    del instances
                    gc.collect()
    
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
        with self._lock:
            self._singletons.clear()
            self._weak_singletons.clear()
            self._scoped_instances.clear()
        gc.collect()

class TraditionalContainer:
    """传统容器（用于对比）"""
    
    def __init__(self):
        self._singletons: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
    
    def register_singleton(self, name: str, instance: Any):
        """注册单例服务"""
        self._singletons[name] = instance
    
    def register_factory(self, name: str, factory: Callable):
        """注册工厂函数"""
        self._factories[name] = factory
    
    def get(self, name: str) -> Any:
        """获取服务实例"""
        if name in self._singletons:
            return self._singletons[name]
        elif name in self._factories:
            return self._factories[name]()
        else:
            raise ValueError(f"Service '{name}' not registered")

class ContainerOptimizationTest:
    """容器优化测试类"""
    
    def __init__(self):
        self.results = {}
    
    def test_traditional_container_memory(self) -> Dict:
        """测试传统容器内存使用"""
        print("\n🔍 测试传统容器内存使用...")
        
        results = {}
        
        try:
            with memory_profiler("traditional_container") as profiler:
                profiler.start_monitoring()
                
                # 创建传统容器
                container = TraditionalContainer()
                profiler.take_snapshot("after_container_init")
                
                # 模拟大量服务创建
                class TestService:
                    def __init__(self):
                        self.data = "x" * 10000  # 10KB数据
                        self.timestamp = time.time()
                
                # 注册并获取大量服务
                services = []
                for i in range(100):
                    service_name = f"test_service_{i}"
                    container.register_singleton(service_name, TestService())
                    service = container.get(service_name)
                    services.append(service)
                    
                    if i % 20 == 0:
                        profiler.take_snapshot(f"after_{i}_services")
                
                profiler.take_snapshot("after_all_services")
                
                # 清理
                del services
                del container
                gc.collect()
                profiler.take_snapshot("after_cleanup")
            
            peak = profiler.get_peak_memory()
            growth = profiler.get_memory_growth()
            
            results = {
                "peak_memory_mb": peak.rss_mb,
                "memory_growth_rate": growth,
                "success": True
            }
            
            print(f"    传统容器峰值内存: {peak.rss_mb:.1f} MB")
            
        except Exception as e:
            print(f"    ❌ 传统容器测试失败: {e}")
            results = {"success": False, "error": str(e)}
        
        return results
    
    def test_optimized_container_memory(self) -> Dict:
        """测试优化容器内存使用"""
        print("\n🚀 测试优化容器内存使用...")
        
        results = {}
        
        try:
            with memory_profiler("optimized_container") as profiler:
                profiler.start_monitoring()
                
                # 创建优化容器
                container = SimpleOptimizedContainer()
                profiler.take_snapshot("after_container_init")
                
                # 模拟大量服务创建
                class TestService:
                    def __init__(self):
                        self.data = "x" * 10000  # 10KB数据
                        self.timestamp = time.time()
                
                # 使用不同作用域注册服务
                services = []
                
                # 单例服务
                for i in range(20):
                    service_name = f"singleton_service_{i}"
                    container.register_singleton(service_name, TestService())
                    service = container.get(service_name)
                    services.append(service)
                
                profiler.take_snapshot("after_singleton_services")
                
                # 弱引用单例服务
                weak_services = []
                for i in range(30):
                    service_name = f"weak_service_{i}"
                    container.register_factory(service_name, TestService, ServiceScope.WEAK_SINGLETON)
                    service = container.get(service_name)
                    weak_services.append(weakref.ref(service))
                    services.append(service)
                
                profiler.take_snapshot("after_weak_singleton_services")
                
                # 作用域服务
                with container.scope("test_scope_1"):
                    for i in range(25):
                        service_name = f"scoped_service_{i}"
                        container.register_factory(service_name, TestService, ServiceScope.SCOPED)
                        service = container.get(service_name)
                        # 不保存引用，让它们在作用域结束时被清理
                
                profiler.take_snapshot("after_scoped_services")
                
                # 瞬态服务
                for i in range(25):
                    service_name = f"transient_service_{i}"
                    container.register_factory(service_name, TestService, ServiceScope.TRANSIENT)
                    service = container.get(service_name)
                    # 不保存引用，让它们立即被垃圾回收
                
                profiler.take_snapshot("after_transient_services")
                
                # 获取统计信息
                stats = container.get_stats()
                print(f"    容器统计: {stats}")
                
                # 清理部分引用，测试弱引用清理
                del services[20:50]  # 删除弱引用服务的强引用
                gc.collect()
                profiler.take_snapshot("after_partial_cleanup")
                
                # 最终清理
                container.shutdown()
                del container, services
                gc.collect()
                profiler.take_snapshot("after_final_cleanup")
            
            peak = profiler.get_peak_memory()
            growth = profiler.get_memory_growth()
            
            results = {
                "peak_memory_mb": peak.rss_mb,
                "memory_growth_rate": growth,
                "container_stats": stats,
                "success": True
            }
            
            print(f"    优化容器峰值内存: {peak.rss_mb:.1f} MB")
            
        except Exception as e:
            print(f"    ❌ 优化容器测试失败: {e}")
            results = {"success": False, "error": str(e)}
        
        return results
    
    def run_container_optimization_tests(self) -> Dict:
        """运行所有容器优化测试"""
        print("🔍 依赖注入容器生命周期优化测试")
        print("=" * 60)
        
        # 运行各项测试
        traditional_results = self.test_traditional_container_memory()
        optimized_results = self.test_optimized_container_memory()
        
        self.results = {
            "traditional_container": traditional_results,
            "optimized_container": optimized_results
        }
        
        self.print_optimization_summary()
        return self.results
    
    def print_optimization_summary(self):
        """打印优化效果摘要"""
        print("\n📊 容器优化效果摘要:")
        print("=" * 60)
        
        traditional = self.results.get("traditional_container", {})
        optimized = self.results.get("optimized_container", {})
        
        if traditional.get("success") and optimized.get("success"):
            traditional_peak = traditional["peak_memory_mb"]
            optimized_peak = optimized["peak_memory_mb"]
            memory_reduction = traditional_peak - optimized_peak
            reduction_percent = (memory_reduction / traditional_peak) * 100
            
            print(f"内存使用优化:")
            print(f"  传统容器峰值: {traditional_peak:.1f} MB")
            print(f"  优化容器峰值: {optimized_peak:.1f} MB")
            print(f"  内存减少: {memory_reduction:.1f} MB ({reduction_percent:.1f}%)")
        
        print("\n🎯 优化建议:")
        print("1. 使用作用域管理服务生命周期")
        print("2. 对大对象使用弱引用单例")
        print("3. 及时清理不需要的作用域")
        print("4. 监控容器统计信息")

def main():
    """主函数"""
    print("🔍 依赖注入容器生命周期优化测试工具")
    print("=" * 60)
    
    # 运行优化测试
    test = ContainerOptimizationTest()
    results = test.run_container_optimization_tests()
    
    # 保存结果
    import json
    with open("container_simple_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 测试结果已保存到: container_simple_results.json")

if __name__ == "__main__":
    main()
