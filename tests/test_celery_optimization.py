#!/usr/bin/env python3
"""
Celery任务内存管理优化测试
验证任务间内存隔离和清理效果
"""

import sys
import os
import gc
import time
import threading
from pathlib import Path
from typing import Dict, List, Tuple
import logging

# 添加项目路径
sys.path.insert(0, str(Path("..").absolute()))
sys.path.insert(0, str(Path("../worker").absolute()))
sys.path.insert(0, str(Path(".").absolute()))

# 导入测试模块
from test_memory_optimization import MemoryProfiler, memory_profiler

logger = logging.getLogger(__name__)

class CeleryOptimizationTest:
    """Celery优化测试类"""
    
    def __init__(self):
        self.results = {}
    
    def test_memory_monitor(self) -> Dict:
        """测试内存监控器"""
        print("\n🔍 测试内存监控器...")
        
        results = {}
        
        try:
            # 导入内存监控器
            sys.path.insert(0, str(Path("../worker/app").absolute()))
            from celery_optimized import MemoryMonitor
            
            monitor = MemoryMonitor()
            
            # 获取初始内存
            initial_stats = monitor.get_stats()
            print(f"    初始内存: {initial_stats['current_memory_mb']:.1f}MB")
            
            # 模拟任务执行
            task_id = "test_task_001"
            task_name = "test_memory_task"
            
            monitor.record_task_start(task_id, task_name)
            
            # 模拟内存使用
            large_data = []
            for i in range(100):
                large_data.append("x" * 10000)  # 每个1KB
                time.sleep(0.001)  # 短暂延迟
            
            # 记录任务结束
            monitor.record_task_end(task_id, success=True)
            
            # 获取最终统计
            final_stats = monitor.get_stats()
            
            results = {
                "initial_memory_mb": initial_stats["current_memory_mb"],
                "final_memory_mb": final_stats["current_memory_mb"],
                "peak_memory_mb": final_stats["peak_memory_mb"],
                "memory_growth_mb": final_stats["memory_growth_mb"],
                "success": True
            }
            
            print(f"    最终内存: {final_stats['current_memory_mb']:.1f}MB")
            print(f"    峰值内存: {final_stats['peak_memory_mb']:.1f}MB")
            print(f"    内存增长: {final_stats['memory_growth_mb']:.1f}MB")
            
            # 清理
            del large_data
            gc.collect()
            
        except Exception as e:
            print(f"    ❌ 内存监控器测试失败: {e}")
            results = {"success": False, "error": str(e)}
        
        return results
    
    def test_task_memory_manager(self) -> Dict:
        """测试任务内存管理器"""
        print("\n🛠️ 测试任务内存管理器...")
        
        results = {}
        
        try:
            from celery_optimized import TaskMemoryManager
            
            # 创建内存管理器（设置较低的限制用于测试）
            manager = TaskMemoryManager(memory_limit_mb=100.0)
            
            # 注册清理回调
            cleanup_called = False
            def test_cleanup():
                nonlocal cleanup_called
                cleanup_called = True
                print("    清理回调被调用")
            
            manager.register_cleanup_callback(test_cleanup)
            
            # 测试任务上下文
            task_id = "test_task_002"
            task_name = "test_context_task"
            
            initial_stats = manager.monitor.get_stats()
            
            with manager.task_context(task_id, task_name):
                # 模拟任务工作
                temp_data = ["x" * 1000 for _ in range(1000)]  # 1MB数据
                time.sleep(0.1)
                del temp_data
            
            final_stats = manager.monitor.get_stats()
            
            results = {
                "initial_memory_mb": initial_stats["current_memory_mb"],
                "final_memory_mb": final_stats["current_memory_mb"],
                "cleanup_called": cleanup_called,
                "memory_limit_mb": manager.memory_limit_mb,
                "success": True
            }
            
            print(f"    内存限制: {manager.memory_limit_mb}MB")
            print(f"    清理回调调用: {cleanup_called}")
            print(f"    内存变化: {initial_stats['current_memory_mb']:.1f}MB -> {final_stats['current_memory_mb']:.1f}MB")
            
        except Exception as e:
            print(f"    ❌ 任务内存管理器测试失败: {e}")
            results = {"success": False, "error": str(e)}
        
        return results
    
    def test_optimized_celery_config(self) -> Dict:
        """测试优化的Celery配置"""
        print("\n⚙️ 测试优化的Celery配置...")
        
        results = {}
        
        try:
            from celery_optimized import create_optimized_celery_app
            
            # 创建优化的Celery应用
            app = create_optimized_celery_app(
                "test_app", 
                "redis://localhost:6379/0", 
                "redis://localhost:6379/0"
            )
            
            # 检查配置
            config = app.conf
            
            results = {
                "worker_max_tasks_per_child": config.get("worker_max_tasks_per_child"),
                "worker_max_memory_per_child": config.get("worker_max_memory_per_child"),
                "worker_prefetch_multiplier": config.get("worker_prefetch_multiplier"),
                "task_acks_late": config.get("task_acks_late"),
                "result_expires": config.get("result_expires"),
                "result_cache_max": config.get("result_cache_max"),
                "task_routes_count": len(config.get("task_routes", {})),
                "success": True
            }
            
            print(f"    每个worker最大任务数: {results['worker_max_tasks_per_child']}")
            print(f"    每个worker最大内存: {results['worker_max_memory_per_child']}KB")
            print(f"    预取倍数: {results['worker_prefetch_multiplier']}")
            print(f"    延迟确认: {results['task_acks_late']}")
            print(f"    结果过期时间: {results['result_expires']}秒")
            print(f"    任务路由数: {results['task_routes_count']}")
            
        except Exception as e:
            print(f"    ❌ Celery配置测试失败: {e}")
            results = {"success": False, "error": str(e)}
        
        return results
    
    def test_memory_optimized_decorator(self) -> Dict:
        """测试内存优化装饰器"""
        print("\n🎯 测试内存优化装饰器...")
        
        results = {}
        
        try:
            from celery_optimized import memory_optimized_task, get_memory_manager
            
            # 模拟Celery任务请求对象
            class MockRequest:
                def __init__(self, task_id: str):
                    self.id = task_id
            
            class MockTask:
                def __init__(self, name: str, task_id: str):
                    self.name = name
                    self.request = MockRequest(task_id)
            
            # 创建被装饰的函数
            @memory_optimized_task
            def test_task(self):
                # 模拟任务工作
                data = ["x" * 10000 for _ in range(100)]  # 1MB数据
                time.sleep(0.1)
                return len(data)
            
            # 创建模拟任务实例
            task_instance = MockTask("test_decorated_task", "test_task_003")
            
            # 获取初始内存统计
            manager = get_memory_manager()
            initial_stats = manager.monitor.get_stats()
            
            # 执行装饰的任务
            result = test_task(task_instance)
            
            # 获取最终内存统计
            final_stats = manager.monitor.get_stats()
            
            results = {
                "task_result": result,
                "initial_memory_mb": initial_stats["current_memory_mb"],
                "final_memory_mb": final_stats["current_memory_mb"],
                "memory_growth_mb": final_stats["memory_growth_mb"],
                "success": True
            }
            
            print(f"    任务结果: {result}")
            print(f"    内存变化: {initial_stats['current_memory_mb']:.1f}MB -> {final_stats['current_memory_mb']:.1f}MB")
            print(f"    总内存增长: {final_stats['memory_growth_mb']:.1f}MB")
            
        except Exception as e:
            print(f"    ❌ 装饰器测试失败: {e}")
            results = {"success": False, "error": str(e)}
        
        return results
    
    def test_memory_cleanup_effectiveness(self) -> Dict:
        """测试内存清理效果"""
        print("\n🧹 测试内存清理效果...")
        
        results = {}
        
        try:
            with memory_profiler("celery_cleanup_test") as profiler:
                profiler.start_monitoring()
                
                from celery_optimized import TaskMemoryManager
                
                manager = TaskMemoryManager(memory_limit_mb=50.0)
                
                profiler.take_snapshot("after_manager_init")
                
                # 模拟多个任务执行
                for i in range(5):
                    task_id = f"cleanup_test_task_{i}"
                    task_name = f"cleanup_task_{i}"
                    
                    with manager.task_context(task_id, task_name):
                        # 创建大量数据
                        large_data = ["x" * 20000 for _ in range(100)]  # 2MB数据
                        time.sleep(0.05)
                        del large_data
                    
                    profiler.take_snapshot(f"after_task_{i}")
                
                # 最终清理
                manager.cleanup_memory()
                profiler.take_snapshot("after_final_cleanup")
            
            peak = profiler.get_peak_memory()
            growth = profiler.get_memory_growth()
            
            results = {
                "peak_memory_mb": peak.rss_mb,
                "memory_growth_rate": growth,
                "tasks_executed": 5,
                "success": True
            }
            
            print(f"    执行任务数: 5")
            print(f"    峰值内存: {peak.rss_mb:.1f}MB")
            print(f"    内存增长率: {growth:.2f}")
            
        except Exception as e:
            print(f"    ❌ 内存清理测试失败: {e}")
            results = {"success": False, "error": str(e)}
        
        return results
    
    def run_celery_optimization_tests(self) -> Dict:
        """运行所有Celery优化测试"""
        print("🔍 Celery任务内存管理优化测试")
        print("=" * 60)
        
        # 运行各项测试
        monitor_results = self.test_memory_monitor()
        manager_results = self.test_task_memory_manager()
        config_results = self.test_optimized_celery_config()
        decorator_results = self.test_memory_optimized_decorator()
        cleanup_results = self.test_memory_cleanup_effectiveness()
        
        self.results = {
            "memory_monitor": monitor_results,
            "task_memory_manager": manager_results,
            "optimized_config": config_results,
            "memory_decorator": decorator_results,
            "cleanup_effectiveness": cleanup_results
        }
        
        self.print_optimization_summary()
        return self.results
    
    def print_optimization_summary(self):
        """打印优化效果摘要"""
        print("\n📊 Celery优化效果摘要:")
        print("=" * 60)
        
        monitor_results = self.results.get("memory_monitor", {})
        if monitor_results.get("success"):
            print(f"内存监控:")
            print(f"  峰值内存: {monitor_results['peak_memory_mb']:.1f}MB")
            print(f"  内存增长: {monitor_results['memory_growth_mb']:.1f}MB")
        
        manager_results = self.results.get("task_memory_manager", {})
        if manager_results.get("success"):
            print(f"任务内存管理:")
            print(f"  内存限制: {manager_results['memory_limit_mb']}MB")
            print(f"  清理回调: {manager_results['cleanup_called']}")
        
        config_results = self.results.get("optimized_config", {})
        if config_results.get("success"):
            print(f"优化配置:")
            print(f"  每worker最大任务: {config_results['worker_max_tasks_per_child']}")
            print(f"  内存限制: {config_results['worker_max_memory_per_child']}KB")
        
        cleanup_results = self.results.get("cleanup_effectiveness", {})
        if cleanup_results.get("success"):
            print(f"清理效果:")
            print(f"  峰值内存: {cleanup_results['peak_memory_mb']:.1f}MB")
            print(f"  内存增长率: {cleanup_results['memory_growth_rate']:.2f}")
        
        print("\n🎯 优化建议:")
        print("1. 使用内存监控和限制")
        print("2. 实现任务间内存隔离")
        print("3. 配置合理的worker参数")
        print("4. 定期清理任务内存")

def main():
    """主函数"""
    print("🔍 Celery任务内存管理优化测试工具")
    print("=" * 60)
    
    # 运行优化测试
    test = CeleryOptimizationTest()
    results = test.run_celery_optimization_tests()
    
    # 保存结果
    import json
    with open("celery_optimization_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 测试结果已保存到: celery_optimization_results.json")

if __name__ == "__main__":
    main()
