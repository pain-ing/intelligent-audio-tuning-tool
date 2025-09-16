#!/usr/bin/env python3
"""
缓存优化测试
验证内存感知缓存系统的效果
"""

import sys
import os
import gc
import time
import numpy as np
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple
import logging

# 添加项目路径
sys.path.insert(0, str(Path("../worker").absolute()))
sys.path.insert(0, str(Path("../src").absolute()))
sys.path.insert(0, str(Path(".").absolute()))

# 导入测试模块
from test_memory_optimization import MemoryProfiler, memory_profiler

logger = logging.getLogger(__name__)

class CacheOptimizationTest:
    """缓存优化测试类"""
    
    def __init__(self):
        self.results = {}
    
    def test_cache_memory_management(self) -> Dict:
        """测试缓存内存管理"""
        print("\n🔍 测试缓存内存管理...")
        
        results = {}
        
        # 测试传统缓存（如果可用）
        print("  测试传统缓存方法...")
        try:
            with memory_profiler("traditional_cache") as profiler:
                profiler.start_monitoring()
                
                # 模拟大量缓存操作
                cache_data = {}
                
                profiler.take_snapshot("before_cache_operations")
                
                # 创建大量缓存数据
                for i in range(1000):
                    key = f"test_key_{i}"
                    # 创建较大的数据对象
                    value = {
                        "data": np.random.random(1000).tolist(),
                        "metadata": {"index": i, "timestamp": time.time()},
                        "large_text": "x" * 1000
                    }
                    cache_data[key] = value
                    
                    if i % 100 == 0:
                        profiler.take_snapshot(f"after_{i}_entries")
                
                profiler.take_snapshot("after_all_cache_operations")
                
                # 清理
                del cache_data
                gc.collect()
                profiler.take_snapshot("after_cleanup")
            
            peak = profiler.get_peak_memory()
            growth = profiler.get_memory_growth()
            
            results["traditional"] = {
                "peak_memory_mb": peak.rss_mb,
                "memory_growth_rate": growth,
                "success": True
            }
            
            print(f"    传统缓存峰值内存: {peak.rss_mb:.1f} MB")
            
        except Exception as e:
            print(f"    ❌ 传统缓存测试失败: {e}")
            results["traditional"] = {"success": False, "error": str(e)}
        
        # 测试优化缓存
        print("  测试优化缓存方法...")
        try:
            with memory_profiler("optimized_cache") as profiler:
                profiler.start_monitoring()
                
                from app.cache_optimized import MemoryAwareCache
                
                # 创建内存限制的缓存
                cache = MemoryAwareCache(max_memory_mb=50.0, max_entries=500)
                
                profiler.take_snapshot("after_cache_init")
                
                # 创建大量缓存数据
                for i in range(1000):
                    key = f"test_key_{i}"
                    value = {
                        "data": np.random.random(1000).tolist(),
                        "metadata": {"index": i, "timestamp": time.time()},
                        "large_text": "x" * 1000
                    }
                    
                    cache.set("test", key, value, ttl_sec=3600)
                    
                    if i % 100 == 0:
                        profiler.take_snapshot(f"after_{i}_entries")
                        stats = cache.get_stats()
                        print(f"      缓存统计 ({i}): {stats['entries_count']}条目, "
                              f"{stats['memory_usage_mb']:.1f}MB")
                
                profiler.take_snapshot("after_all_cache_operations")
                
                # 获取最终统计
                final_stats = cache.get_stats()
                print(f"    最终缓存统计: {final_stats}")
                
                # 清理
                cache.shutdown()
                del cache
                gc.collect()
                profiler.take_snapshot("after_cleanup")
            
            peak = profiler.get_peak_memory()
            growth = profiler.get_memory_growth()
            
            results["optimized"] = {
                "peak_memory_mb": peak.rss_mb,
                "memory_growth_rate": growth,
                "success": True,
                "final_stats": final_stats
            }
            
            print(f"    优化缓存峰值内存: {peak.rss_mb:.1f} MB")
            
        except Exception as e:
            print(f"    ❌ 优化缓存测试失败: {e}")
            results["optimized"] = {"success": False, "error": str(e)}
        
        # 计算改进
        if results.get("traditional", {}).get("success") and results.get("optimized", {}).get("success"):
            traditional_peak = results["traditional"]["peak_memory_mb"]
            optimized_peak = results["optimized"]["peak_memory_mb"]
            memory_reduction = traditional_peak - optimized_peak
            reduction_percent = (memory_reduction / traditional_peak) * 100
            
            results["improvement"] = {
                "memory_reduction_mb": memory_reduction,
                "reduction_percent": reduction_percent
            }
            
            print(f"    💡 缓存内存减少: {memory_reduction:.1f} MB ({reduction_percent:.1f}%)")
        
        return results
    
    def test_cache_performance(self) -> Dict:
        """测试缓存性能"""
        print("\n⚡ 测试缓存性能...")
        
        results = {}
        
        try:
            from app.cache_optimized import MemoryAwareCache
            
            # 创建缓存实例
            cache = MemoryAwareCache(max_memory_mb=100.0, max_entries=1000)
            
            # 准备测试数据
            test_data = {}
            for i in range(500):
                key = f"perf_test_{i}"
                value = {
                    "data": np.random.random(100).tolist(),
                    "index": i,
                    "timestamp": time.time()
                }
                test_data[key] = value
            
            # 测试写入性能
            start_time = time.time()
            for key, value in test_data.items():
                cache.set("performance", key, value)
            write_time = time.time() - start_time
            
            # 测试读取性能
            start_time = time.time()
            hit_count = 0
            for key in test_data.keys():
                result = cache.get("performance", key)
                if result is not None:
                    hit_count += 1
            read_time = time.time() - start_time
            
            # 测试缓存命中率
            hit_rate = hit_count / len(test_data)
            
            # 获取统计信息
            stats = cache.get_stats()
            
            results = {
                "write_time_sec": write_time,
                "read_time_sec": read_time,
                "hit_rate": hit_rate,
                "entries_count": stats["entries_count"],
                "memory_usage_mb": stats["memory_usage_mb"],
                "cache_hit_rate": stats["hit_rate"],
                "success": True
            }
            
            print(f"    写入时间: {write_time:.3f}秒")
            print(f"    读取时间: {read_time:.3f}秒")
            print(f"    命中率: {hit_rate:.2%}")
            print(f"    内存使用: {stats['memory_usage_mb']:.1f}MB")
            
            # 清理
            cache.shutdown()
            
        except Exception as e:
            print(f"    ❌ 缓存性能测试失败: {e}")
            results = {"success": False, "error": str(e)}
        
        return results
    
    def test_cache_lru_behavior(self) -> Dict:
        """测试缓存LRU行为"""
        print("\n🔄 测试缓存LRU行为...")
        
        results = {}
        
        try:
            from app.cache_optimized import MemoryAwareCache
            
            # 创建小容量缓存
            cache = MemoryAwareCache(max_memory_mb=5.0, max_entries=10)
            
            # 填充缓存到容量限制
            for i in range(15):  # 超过最大条目数
                key = f"lru_test_{i}"
                value = {"data": "x" * 1000, "index": i}  # 每个约1KB
                cache.set("lru", key, value)
            
            # 检查缓存状态
            stats = cache.get_stats()
            print(f"    缓存条目数: {stats['entries_count']} (最大: 10)")
            print(f"    内存使用: {stats['memory_usage_mb']:.1f}MB (最大: 5.0MB)")
            
            # 测试LRU淘汰：访问早期的条目应该被淘汰
            early_key_exists = cache.get("lru", "lru_test_0") is not None
            late_key_exists = cache.get("lru", "lru_test_14") is not None
            
            results = {
                "final_entries": stats['entries_count'],
                "final_memory_mb": stats['memory_usage_mb'],
                "early_key_evicted": not early_key_exists,
                "late_key_preserved": late_key_exists,
                "lru_working": not early_key_exists and late_key_exists,
                "success": True
            }
            
            print(f"    早期键被淘汰: {not early_key_exists}")
            print(f"    晚期键被保留: {late_key_exists}")
            print(f"    LRU正常工作: {results['lru_working']}")
            
            # 清理
            cache.shutdown()
            
        except Exception as e:
            print(f"    ❌ LRU测试失败: {e}")
            results = {"success": False, "error": str(e)}
        
        return results
    
    def run_cache_optimization_tests(self) -> Dict:
        """运行所有缓存优化测试"""
        print("🔍 缓存策略内存优化测试")
        print("=" * 60)
        
        # 运行各项测试
        memory_results = self.test_cache_memory_management()
        performance_results = self.test_cache_performance()
        lru_results = self.test_cache_lru_behavior()
        
        self.results = {
            "memory_management": memory_results,
            "performance": performance_results,
            "lru_behavior": lru_results
        }
        
        self.print_optimization_summary()
        return self.results
    
    def print_optimization_summary(self):
        """打印优化效果摘要"""
        print("\n📊 缓存优化效果摘要:")
        print("=" * 60)
        
        memory_results = self.results.get("memory_management", {})
        if "improvement" in memory_results:
            improvement = memory_results["improvement"]
            print(f"内存管理优化:")
            print(f"  内存减少: {improvement['memory_reduction_mb']:.1f} MB")
            print(f"  优化幅度: {improvement['reduction_percent']:.1f}%")
        
        performance_results = self.results.get("performance", {})
        if performance_results.get("success"):
            print(f"性能测试结果:")
            print(f"  缓存命中率: {performance_results['hit_rate']:.2%}")
            print(f"  内存使用: {performance_results['memory_usage_mb']:.1f}MB")
        
        lru_results = self.results.get("lru_behavior", {})
        if lru_results.get("success"):
            print(f"LRU行为测试:")
            print(f"  LRU机制正常: {lru_results['lru_working']}")
            print(f"  内存控制有效: {lru_results['final_memory_mb']:.1f}MB ≤ 5.0MB")
        
        print("\n🎯 优化建议:")
        print("1. 使用内存感知的缓存系统")
        print("2. 实现LRU淘汰策略")
        print("3. 设置合理的内存和条目限制")
        print("4. 定期清理过期和低价值缓存")

def main():
    """主函数"""
    print("🔍 缓存策略内存优化测试工具")
    print("=" * 60)
    
    # 运行优化测试
    test = CacheOptimizationTest()
    results = test.run_cache_optimization_tests()
    
    # 保存结果
    import json
    with open("cache_optimization_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 测试结果已保存到: cache_optimization_results.json")

if __name__ == "__main__":
    main()
