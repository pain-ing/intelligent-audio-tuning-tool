#!/usr/bin/env python3
"""
依赖注入容器优化测试
验证容器生命周期管理和内存优化效果
"""

import sys
import os
import gc
import time
import weakref
from pathlib import Path
from typing import Dict, List, Tuple
import logging

# 添加项目路径
sys.path.insert(0, str(Path("..").absolute()))
sys.path.insert(0, str(Path("../src").absolute()))
sys.path.insert(0, str(Path("../worker").absolute()))
sys.path.insert(0, str(Path(".").absolute()))

# 导入测试模块
from test_memory_optimization import MemoryProfiler, memory_profiler

logger = logging.getLogger(__name__)

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
                
                from src.core.container import DIContainer
                
                # 创建传统容器
                container = DIContainer()
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
                
                from src.core.container_optimized import MemoryOptimizedDIContainer, ServiceScope
                
                # 创建优化容器
                container = MemoryOptimizedDIContainer()
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
                
                # 等待一下让清理线程工作
                time.sleep(2)
                profiler.take_snapshot("after_cleanup_wait")
                
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
    
    def test_scope_lifecycle(self) -> Dict:
        """测试作用域生命周期"""
        print("\n🔄 测试作用域生命周期...")
        
        results = {}
        
        try:
            from src.core.container_optimized import MemoryOptimizedDIContainer, ServiceScope
            
            container = MemoryOptimizedDIContainer()
            
            class TestService:
                def __init__(self):
                    self.id = id(self)
                    self.data = "x" * 1000
            
            # 注册作用域服务
            container.register_factory("scoped_test", TestService, ServiceScope.SCOPED)
            
            # 测试作用域隔离
            scope1_instances = []
            with container.scope("scope1"):
                for _ in range(5):
                    instance = container.get("scoped_test")
                    scope1_instances.append(instance.id)
            
            scope2_instances = []
            with container.scope("scope2"):
                for _ in range(5):
                    instance = container.get("scoped_test")
                    scope2_instances.append(instance.id)
            
            # 检查作用域隔离
            scope1_unique = len(set(scope1_instances))
            scope2_unique = len(set(scope2_instances))
            scopes_isolated = not (set(scope1_instances) & set(scope2_instances))
            
            # 检查作用域内单例
            scope1_singleton = scope1_unique == 1
            scope2_singleton = scope2_unique == 1
            
            # 获取统计信息
            stats = container.get_stats()
            
            results = {
                "scope1_instances": len(scope1_instances),
                "scope2_instances": len(scope2_instances),
                "scope1_singleton": scope1_singleton,
                "scope2_singleton": scope2_singleton,
                "scopes_isolated": scopes_isolated,
                "active_scopes": stats["active_scopes_count"],
                "success": True
            }
            
            print(f"    作用域1单例: {scope1_singleton}")
            print(f"    作用域2单例: {scope2_singleton}")
            print(f"    作用域隔离: {scopes_isolated}")
            print(f"    活跃作用域: {stats['active_scopes_count']}")
            
            container.shutdown()
            
        except Exception as e:
            print(f"    ❌ 作用域测试失败: {e}")
            results = {"success": False, "error": str(e)}
        
        return results
    
    def test_weak_reference_cleanup(self) -> Dict:
        """测试弱引用清理"""
        print("\n🧹 测试弱引用清理...")
        
        results = {}
        
        try:
            from src.core.container_optimized import MemoryOptimizedDIContainer, ServiceScope
            
            container = MemoryOptimizedDIContainer()
            
            class TestService:
                def __init__(self):
                    self.data = "x" * 10000  # 10KB
            
            # 注册弱引用单例
            container.register_factory("weak_test", TestService, ServiceScope.WEAK_SINGLETON)
            
            # 创建实例并立即释放
            initial_stats = container.get_stats()
            
            # 创建并保持引用
            instance1 = container.get("weak_test")
            instance2 = container.get("weak_test")  # 应该是同一个实例
            
            same_instance = instance1 is instance2
            
            mid_stats = container.get_stats()
            
            # 释放引用
            del instance1, instance2
            gc.collect()
            
            # 再次获取，应该创建新实例
            instance3 = container.get("weak_test")
            del instance3
            gc.collect()
            
            # 等待清理
            time.sleep(1)
            final_stats = container.get_stats()
            
            results = {
                "same_instance": same_instance,
                "initial_weak_singletons": initial_stats["weak_singletons_count"],
                "mid_weak_singletons": mid_stats["weak_singletons_count"],
                "final_weak_singletons": final_stats["weak_singletons_count"],
                "cleanup_count": final_stats["cleanup_count"],
                "success": True
            }
            
            print(f"    弱引用单例正常: {same_instance}")
            print(f"    清理计数: {final_stats['cleanup_count']}")
            
            container.shutdown()
            
        except Exception as e:
            print(f"    ❌ 弱引用测试失败: {e}")
            results = {"success": False, "error": str(e)}
        
        return results
    
    def run_container_optimization_tests(self) -> Dict:
        """运行所有容器优化测试"""
        print("🔍 依赖注入容器生命周期优化测试")
        print("=" * 60)
        
        # 运行各项测试
        traditional_results = self.test_traditional_container_memory()
        optimized_results = self.test_optimized_container_memory()
        scope_results = self.test_scope_lifecycle()
        weak_ref_results = self.test_weak_reference_cleanup()
        
        self.results = {
            "traditional_container": traditional_results,
            "optimized_container": optimized_results,
            "scope_lifecycle": scope_results,
            "weak_reference_cleanup": weak_ref_results
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
        
        scope_results = self.results.get("scope_lifecycle", {})
        if scope_results.get("success"):
            print(f"作用域管理:")
            print(f"  作用域隔离: {scope_results['scopes_isolated']}")
            print(f"  作用域内单例: {scope_results['scope1_singleton'] and scope_results['scope2_singleton']}")
        
        weak_ref_results = self.results.get("weak_reference_cleanup", {})
        if weak_ref_results.get("success"):
            print(f"弱引用管理:")
            print(f"  弱引用单例正常: {weak_ref_results['same_instance']}")
            print(f"  自动清理有效: {weak_ref_results['cleanup_count'] > 0}")
        
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
    with open("container_optimization_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 测试结果已保存到: container_optimization_results.json")

if __name__ == "__main__":
    main()
