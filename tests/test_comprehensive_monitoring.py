#!/usr/bin/env python3
"""
综合内存监控和性能测试
整合所有优化模块的监控和性能验证
"""

import sys
import os
import gc
import time
import json
import threading
from pathlib import Path
from typing import Dict, List, Tuple, Any
import logging
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path("..").absolute()))
sys.path.insert(0, str(Path("../worker").absolute()))
sys.path.insert(0, str(Path("../api").absolute()))
sys.path.insert(0, str(Path(".").absolute()))

# 导入测试模块
from test_memory_optimization import MemoryProfiler, memory_profiler

logger = logging.getLogger(__name__)

class ComprehensiveMonitoringTest:
    """综合监控测试类"""
    
    def __init__(self):
        self.results = {}
        self.test_audio_file = None
        self.setup_test_environment()
    
    def setup_test_environment(self):
        """设置测试环境"""
        # 查找测试音频文件
        possible_paths = [
            "test_audio.wav",
            "../test_audio.wav",
            "../worker/test_audio.wav",
            "../api/test_audio.wav"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                self.test_audio_file = path
                break
        
        if not self.test_audio_file:
            print("⚠️ 未找到测试音频文件，将创建模拟数据")
    
    def test_streaming_optimization_monitoring(self) -> Dict:
        """测试音频流处理优化监控"""
        print("\n🎵 测试音频流处理优化监控...")
        
        results = {}
        
        try:
            with memory_profiler("streaming_monitoring") as profiler:
                profiler.start_monitoring()
                
                # 导入流处理模块
                sys.path.insert(0, str(Path("../worker/app").absolute()))
                
                try:
                    from audio_streaming import MemoryAwareAudioLoader, StreamingAudioProcessor
                    
                    # 创建内存感知的音频加载器
                    loader = MemoryAwareAudioLoader(target_memory_mb=50.0)
                    
                    profiler.take_snapshot("after_loader_creation")
                    
                    if self.test_audio_file and os.path.exists(self.test_audio_file):
                        # 使用真实音频文件
                        audio_chunk = loader.load_audio_chunk(self.test_audio_file)
                        
                        profiler.take_snapshot("after_audio_loading")
                        
                        # 创建流处理器
                        processor = StreamingAudioProcessor(chunk_size_mb=10.0)
                        
                        # 模拟流处理
                        for i in range(3):
                            processed = processor.process_chunk(audio_chunk.audio_data, audio_chunk.sample_rate)
                            profiler.take_snapshot(f"after_processing_{i}")
                        
                        results["audio_file_used"] = True
                        results["chunk_size_mb"] = audio_chunk.size_mb
                        
                    else:
                        # 使用模拟数据
                        import numpy as np
                        
                        # 创建模拟音频数据（10秒，44.1kHz，立体声）
                        sample_rate = 44100
                        duration = 10
                        samples = sample_rate * duration * 2  # 立体声
                        
                        audio_data = np.random.random(samples).astype(np.float32)
                        
                        profiler.take_snapshot("after_mock_audio_creation")
                        
                        # 模拟流处理
                        processor = StreamingAudioProcessor(chunk_size_mb=10.0)
                        
                        for i in range(3):
                            processed = processor.process_chunk(audio_data, sample_rate)
                            profiler.take_snapshot(f"after_mock_processing_{i}")
                        
                        results["audio_file_used"] = False
                        results["mock_data_size_mb"] = audio_data.nbytes / (1024 * 1024)
                    
                except ImportError as e:
                    print(f"    ⚠️ 流处理模块不可用: {e}")
                    results["streaming_available"] = False
                    
                    # 创建简化的内存测试
                    import numpy as np
                    large_array = np.random.random(1000000).astype(np.float32)
                    profiler.take_snapshot("after_large_array")
                    del large_array
                    profiler.take_snapshot("after_array_deletion")
            
            peak = profiler.get_peak_memory()
            growth = profiler.get_memory_growth()
            
            results.update({
                "peak_memory_mb": peak.rss_mb,
                "memory_growth_rate": growth,
                "success": True
            })
            
            print(f"    流处理峰值内存: {peak.rss_mb:.1f}MB")
            print(f"    内存增长率: {growth:.2f}")
            
        except Exception as e:
            print(f"    ❌ 流处理监控测试失败: {e}")
            results = {"success": False, "error": str(e)}
        
        return results
    
    def test_cache_optimization_monitoring(self) -> Dict:
        """测试缓存优化监控"""
        print("\n💾 测试缓存优化监控...")
        
        results = {}
        
        try:
            with memory_profiler("cache_monitoring") as profiler:
                profiler.start_monitoring()
                
                sys.path.insert(0, str(Path("../worker/app").absolute()))
                
                try:
                    from cache_optimized import MemoryAwareCache
                    
                    # 创建内存感知缓存
                    cache = MemoryAwareCache(
                        max_memory_mb=30.0,
                        max_items=100,
                        cleanup_threshold=0.8
                    )
                    
                    profiler.take_snapshot("after_cache_creation")
                    
                    # 填充缓存
                    for i in range(50):
                        key = f"test_key_{i}"
                        value = f"test_value_{i}" * 1000  # 每个值约1KB
                        cache.set(key, value)
                        
                        if i % 10 == 0:
                            profiler.take_snapshot(f"after_cache_fill_{i}")
                    
                    # 获取缓存统计
                    cache_stats = cache.get_stats()
                    
                    # 触发清理
                    cache.cleanup()
                    profiler.take_snapshot("after_cache_cleanup")
                    
                    final_stats = cache.get_stats()
                    
                    results.update({
                        "initial_stats": cache_stats,
                        "final_stats": final_stats,
                        "cache_available": True
                    })
                    
                    print(f"    缓存项数: {cache_stats['item_count']} -> {final_stats['item_count']}")
                    print(f"    缓存内存: {cache_stats['memory_usage_mb']:.1f}MB -> {final_stats['memory_usage_mb']:.1f}MB")
                    
                except ImportError as e:
                    print(f"    ⚠️ 缓存模块不可用: {e}")
                    results["cache_available"] = False
                    
                    # 简化的缓存测试
                    simple_cache = {}
                    for i in range(50):
                        simple_cache[f"key_{i}"] = f"value_{i}" * 1000
                    
                    profiler.take_snapshot("after_simple_cache")
                    simple_cache.clear()
                    profiler.take_snapshot("after_simple_cleanup")
            
            peak = profiler.get_peak_memory()
            growth = profiler.get_memory_growth()
            
            results.update({
                "peak_memory_mb": peak.rss_mb,
                "memory_growth_rate": growth,
                "success": True
            })
            
            print(f"    缓存峰值内存: {peak.rss_mb:.1f}MB")
            
        except Exception as e:
            print(f"    ❌ 缓存监控测试失败: {e}")
            results = {"success": False, "error": str(e)}
        
        return results
    
    def test_feature_extraction_monitoring(self) -> Dict:
        """测试特征提取优化监控"""
        print("\n🔍 测试特征提取优化监控...")
        
        results = {}
        
        try:
            with memory_profiler("feature_monitoring") as profiler:
                profiler.start_monitoring()
                
                sys.path.insert(0, str(Path("../worker/app").absolute()))
                
                try:
                    from audio_features_optimized import MemoryOptimizedFeatureExtractor
                    
                    # 创建优化的特征提取器
                    extractor = MemoryOptimizedFeatureExtractor(
                        buffer_size=8192,
                        enable_cache=True
                    )
                    
                    profiler.take_snapshot("after_extractor_creation")
                    
                    # 创建模拟音频数据
                    import numpy as np
                    sample_rate = 22050
                    duration = 5  # 5秒音频
                    audio_data = np.random.random(sample_rate * duration).astype(np.float32)
                    
                    profiler.take_snapshot("after_audio_creation")
                    
                    # 提取不同特征
                    stft_features = extractor.extract_stft_features_optimized(audio_data, sample_rate)
                    profiler.take_snapshot("after_stft_extraction")
                    
                    mel_features = extractor.extract_mel_features_optimized(audio_data, sample_rate)
                    profiler.take_snapshot("after_mel_extraction")
                    
                    # 获取统计信息
                    stats = extractor.get_stats()
                    
                    results.update({
                        "extractor_stats": stats,
                        "stft_shape": stft_features.shape if hasattr(stft_features, 'shape') else None,
                        "mel_shape": mel_features.shape if hasattr(mel_features, 'shape') else None,
                        "feature_extraction_available": True
                    })
                    
                    print(f"    STFT特征形状: {stft_features.shape if hasattr(stft_features, 'shape') else 'N/A'}")
                    print(f"    Mel特征形状: {mel_features.shape if hasattr(mel_features, 'shape') else 'N/A'}")
                    print(f"    缓存命中率: {stats.get('cache_hit_rate', 0):.1f}%")
                    
                except ImportError as e:
                    print(f"    ⚠️ 特征提取模块不可用: {e}")
                    results["feature_extraction_available"] = False
                    
                    # 简化的特征提取测试
                    import numpy as np
                    audio_data = np.random.random(22050 * 5).astype(np.float32)
                    
                    # 模拟STFT计算
                    stft_result = np.fft.fft(audio_data[:1024])
                    profiler.take_snapshot("after_simple_fft")
            
            peak = profiler.get_peak_memory()
            growth = profiler.get_memory_growth()
            
            results.update({
                "peak_memory_mb": peak.rss_mb,
                "memory_growth_rate": growth,
                "success": True
            })
            
            print(f"    特征提取峰值内存: {peak.rss_mb:.1f}MB")
            
        except Exception as e:
            print(f"    ❌ 特征提取监控测试失败: {e}")
            results = {"success": False, "error": str(e)}
        
        return results
    
    def test_system_resource_monitoring(self) -> Dict:
        """测试系统资源监控"""
        print("\n🖥️ 测试系统资源监控...")
        
        results = {}
        
        try:
            import psutil
            
            # 获取初始系统状态
            initial_memory = psutil.virtual_memory()
            initial_cpu = psutil.cpu_percent(interval=1)
            
            # 模拟高负载工作
            start_time = time.time()
            
            # CPU密集型任务
            cpu_work_start = time.time()
            result = sum(i * i for i in range(1000000))
            cpu_work_time = time.time() - cpu_work_start
            
            # 内存密集型任务
            memory_work_start = time.time()
            large_data = [list(range(10000)) for _ in range(100)]
            memory_work_time = time.time() - memory_work_start
            
            # 获取峰值系统状态
            peak_memory = psutil.virtual_memory()
            peak_cpu = psutil.cpu_percent(interval=1)
            
            # 清理
            del large_data
            gc.collect()
            
            # 获取清理后状态
            final_memory = psutil.virtual_memory()
            final_cpu = psutil.cpu_percent(interval=1)
            
            total_time = time.time() - start_time
            
            results = {
                "initial_memory_percent": initial_memory.percent,
                "peak_memory_percent": peak_memory.percent,
                "final_memory_percent": final_memory.percent,
                "initial_cpu_percent": initial_cpu,
                "peak_cpu_percent": peak_cpu,
                "final_cpu_percent": final_cpu,
                "cpu_work_time_sec": cpu_work_time,
                "memory_work_time_sec": memory_work_time,
                "total_time_sec": total_time,
                "memory_recovered": peak_memory.percent - final_memory.percent,
                "success": True
            }
            
            print(f"    内存使用: {initial_memory.percent:.1f}% -> {peak_memory.percent:.1f}% -> {final_memory.percent:.1f}%")
            print(f"    CPU使用: {initial_cpu:.1f}% -> {peak_cpu:.1f}% -> {final_cpu:.1f}%")
            print(f"    内存恢复: {results['memory_recovered']:.1f}%")
            print(f"    总耗时: {total_time:.2f}秒")
            
        except Exception as e:
            print(f"    ❌ 系统资源监控测试失败: {e}")
            results = {"success": False, "error": str(e)}
        
        return results
    
    def run_comprehensive_monitoring_tests(self) -> Dict:
        """运行综合监控测试"""
        print("🔍 综合内存监控和性能测试")
        print("=" * 60)
        
        # 运行各项测试
        streaming_results = self.test_streaming_optimization_monitoring()
        cache_results = self.test_cache_optimization_monitoring()
        feature_results = self.test_feature_extraction_monitoring()
        system_results = self.test_system_resource_monitoring()
        
        self.results = {
            "streaming_optimization": streaming_results,
            "cache_optimization": cache_results,
            "feature_extraction": feature_results,
            "system_resources": system_results,
            "test_timestamp": datetime.now().isoformat(),
            "test_environment": {
                "python_version": sys.version,
                "platform": sys.platform,
                "test_audio_available": self.test_audio_file is not None
            }
        }
        
        self.print_comprehensive_summary()
        return self.results
    
    def print_comprehensive_summary(self):
        """打印综合监控摘要"""
        print("\n📊 综合监控和性能摘要:")
        print("=" * 60)
        
        # 内存使用摘要
        memory_peaks = []
        for test_name, test_results in self.results.items():
            if isinstance(test_results, dict) and test_results.get("success") and "peak_memory_mb" in test_results:
                memory_peaks.append((test_name, test_results["peak_memory_mb"]))
        
        if memory_peaks:
            print("内存使用峰值:")
            for test_name, peak_mb in memory_peaks:
                print(f"  {test_name}: {peak_mb:.1f}MB")
        
        # 系统资源摘要
        system_results = self.results.get("system_resources", {})
        if system_results.get("success"):
            print(f"系统资源:")
            print(f"  内存恢复: {system_results['memory_recovered']:.1f}%")
            print(f"  CPU工作时间: {system_results['cpu_work_time_sec']:.3f}秒")
            print(f"  内存工作时间: {system_results['memory_work_time_sec']:.3f}秒")
        
        # 优化模块可用性
        print("优化模块可用性:")
        streaming_available = self.results.get("streaming_optimization", {}).get("streaming_available", True)
        cache_available = self.results.get("cache_optimization", {}).get("cache_available", True)
        feature_available = self.results.get("feature_extraction", {}).get("feature_extraction_available", True)
        
        print(f"  流处理优化: {'✓' if streaming_available else '✗'}")
        print(f"  缓存优化: {'✓' if cache_available else '✗'}")
        print(f"  特征提取优化: {'✓' if feature_available else '✗'}")
        
        print("\n🎯 监控建议:")
        print("1. 定期监控内存使用峰值")
        print("2. 跟踪系统资源恢复情况")
        print("3. 验证优化模块正常工作")
        print("4. 建立性能基准和告警")

def main():
    """主函数"""
    print("🔍 综合内存监控和性能测试工具")
    print("=" * 60)
    
    # 运行综合监控测试
    test = ComprehensiveMonitoringTest()
    results = test.run_comprehensive_monitoring_tests()
    
    # 保存结果
    with open("comprehensive_monitoring_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 测试结果已保存到: comprehensive_monitoring_results.json")

if __name__ == "__main__":
    main()
