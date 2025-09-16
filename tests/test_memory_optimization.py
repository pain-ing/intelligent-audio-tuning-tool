#!/usr/bin/env python3
"""
内存优化测试和基准测试工具
分析音频处理过程中的内存使用模式，识别内存热点和泄漏风险
"""

import sys
import os
import gc
import time
import psutil
import tracemalloc
import numpy as np
import soundfile as sf
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from contextlib import contextmanager
import threading
import weakref

# 添加项目路径
sys.path.insert(0, str(Path("worker").absolute()))
sys.path.insert(0, str(Path("src").absolute()))

@dataclass
class MemorySnapshot:
    """内存快照数据类"""
    timestamp: float
    rss_mb: float  # 物理内存 (MB)
    vms_mb: float  # 虚拟内存 (MB)
    percent: float  # 内存使用百分比
    tracemalloc_mb: float  # tracemalloc 追踪的内存 (MB)
    gc_objects: int  # GC 对象数量
    description: str

class MemoryProfiler:
    """内存分析器"""
    
    def __init__(self):
        self.process = psutil.Process()
        self.snapshots: List[MemorySnapshot] = []
        self.baseline: Optional[MemorySnapshot] = None
        self._monitoring = False
        self._monitor_thread = None
        
        # 启动 tracemalloc
        tracemalloc.start()
    
    def take_snapshot(self, description: str = "") -> MemorySnapshot:
        """获取内存快照"""
        memory_info = self.process.memory_info()
        memory_percent = self.process.memory_percent()
        
        # tracemalloc 统计
        current, peak = tracemalloc.get_traced_memory()
        
        # GC 统计
        gc_stats = gc.get_stats()
        total_objects = sum(stat['collections'] for stat in gc_stats)
        
        snapshot = MemorySnapshot(
            timestamp=time.time(),
            rss_mb=memory_info.rss / 1024 / 1024,
            vms_mb=memory_info.vms / 1024 / 1024,
            percent=memory_percent,
            tracemalloc_mb=current / 1024 / 1024,
            gc_objects=total_objects,
            description=description
        )
        
        self.snapshots.append(snapshot)
        return snapshot
    
    def set_baseline(self, description: str = "baseline"):
        """设置基准内存使用"""
        self.baseline = self.take_snapshot(description)
    
    def get_memory_diff(self, snapshot: MemorySnapshot) -> Dict[str, float]:
        """计算与基准的内存差异"""
        if not self.baseline:
            return {}
        
        return {
            "rss_diff_mb": snapshot.rss_mb - self.baseline.rss_mb,
            "vms_diff_mb": snapshot.vms_mb - self.baseline.vms_mb,
            "percent_diff": snapshot.percent - self.baseline.percent,
            "tracemalloc_diff_mb": snapshot.tracemalloc_mb - self.baseline.tracemalloc_mb,
            "gc_objects_diff": snapshot.gc_objects - self.baseline.gc_objects
        }
    
    def start_monitoring(self, interval: float = 0.1):
        """开始连续监控内存使用"""
        if self._monitoring:
            return
        
        self._monitoring = True
        
        def monitor():
            while self._monitoring:
                self.take_snapshot("monitoring")
                time.sleep(interval)
        
        self._monitor_thread = threading.Thread(target=monitor, daemon=True)
        self._monitor_thread.start()
    
    def stop_monitoring(self):
        """停止内存监控"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)
    
    def get_peak_memory(self) -> MemorySnapshot:
        """获取峰值内存使用"""
        if not self.snapshots:
            return None
        return max(self.snapshots, key=lambda s: s.rss_mb)
    
    def get_memory_growth(self) -> float:
        """计算内存增长率 (MB/s)"""
        if len(self.snapshots) < 2:
            return 0.0
        
        first = self.snapshots[0]
        last = self.snapshots[-1]
        time_diff = last.timestamp - first.timestamp
        memory_diff = last.rss_mb - first.rss_mb
        
        return memory_diff / time_diff if time_diff > 0 else 0.0
    
    def print_summary(self):
        """打印内存使用摘要"""
        if not self.snapshots:
            print("❌ 没有内存快照数据")
            return
        
        peak = self.get_peak_memory()
        growth_rate = self.get_memory_growth()
        
        print("\n📊 内存使用摘要:")
        print("-" * 50)
        
        if self.baseline:
            print(f"基准内存: {self.baseline.rss_mb:.1f} MB")
            diff = self.get_memory_diff(peak)
            print(f"峰值内存: {peak.rss_mb:.1f} MB (+{diff['rss_diff_mb']:.1f} MB)")
            print(f"内存增长: {diff['rss_diff_mb']:.1f} MB")
        else:
            print(f"峰值内存: {peak.rss_mb:.1f} MB")
        
        print(f"增长率: {growth_rate:.2f} MB/s")
        print(f"快照数量: {len(self.snapshots)}")
        
        # 显示最大的几个快照
        top_snapshots = sorted(self.snapshots, key=lambda s: s.rss_mb, reverse=True)[:5]
        print("\n🔝 内存使用最高的时刻:")
        for i, snapshot in enumerate(top_snapshots, 1):
            print(f"{i}. {snapshot.rss_mb:.1f} MB - {snapshot.description}")

@contextmanager
def memory_profiler(description: str = ""):
    """内存分析上下文管理器"""
    profiler = MemoryProfiler()
    profiler.set_baseline(f"start_{description}")
    
    try:
        yield profiler
    finally:
        profiler.take_snapshot(f"end_{description}")
        profiler.stop_monitoring()

class AudioMemoryBenchmark:
    """音频处理内存基准测试"""
    
    def __init__(self):
        self.results: Dict[str, Dict] = {}
    
    def create_test_audio(self, duration: float = 10.0, sample_rate: int = 48000) -> str:
        """创建测试音频文件"""
        t = np.linspace(0, duration, int(duration * sample_rate), dtype=np.float32)
        
        # 创建复杂音频信号
        audio = 0.3 * np.sin(2 * np.pi * 440 * t)  # 基频
        audio += 0.2 * np.sin(2 * np.pi * 880 * t)  # 二次谐波
        audio += 0.1 * np.sin(2 * np.pi * 1320 * t)  # 三次谐波
        audio += 0.05 * np.random.normal(0, 0.01, len(t))  # 噪声
        
        # 添加包络
        envelope = np.exp(-t / (duration * 0.3))
        audio *= envelope
        
        # 保存到临时文件
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        sf.write(temp_file.name, audio, sample_rate)
        temp_file.close()
        
        return temp_file.name
    
    def benchmark_audio_loading(self, file_path: str) -> Dict:
        """基准测试：音频加载"""
        print("🔍 基准测试：音频加载...")
        
        with memory_profiler("audio_loading") as profiler:
            profiler.start_monitoring()
            
            try:
                from app.audio_analysis import AudioAnalyzer
                analyzer = AudioAnalyzer()
                
                # 测试多次加载
                for i in range(5):
                    profiler.take_snapshot(f"load_iteration_{i}")
                    audio, sr = analyzer.load_audio(file_path)
                    profiler.take_snapshot(f"loaded_iteration_{i}")
                    
                    # 强制释放
                    del audio
                    gc.collect()
                    profiler.take_snapshot(f"gc_iteration_{i}")
                
            except Exception as e:
                print(f"❌ 音频加载测试失败: {e}")
                return {}
        
        peak = profiler.get_peak_memory()
        growth = profiler.get_memory_growth()
        
        result = {
            "peak_memory_mb": peak.rss_mb,
            "memory_growth_rate": growth,
            "snapshots_count": len(profiler.snapshots)
        }
        
        self.results["audio_loading"] = result
        profiler.print_summary()
        return result
    
    def benchmark_feature_extraction(self, file_path: str) -> Dict:
        """基准测试：特征提取"""
        print("\n🔍 基准测试：特征提取...")
        
        with memory_profiler("feature_extraction") as profiler:
            profiler.start_monitoring()
            
            try:
                from app.audio_analysis import AudioAnalyzer
                analyzer = AudioAnalyzer()
                
                profiler.take_snapshot("before_analysis")
                features = analyzer.analyze_features(file_path)
                profiler.take_snapshot("after_analysis")
                
                # 测试缓存效果
                profiler.take_snapshot("before_cached_analysis")
                features_cached = analyzer.analyze_features(file_path)
                profiler.take_snapshot("after_cached_analysis")
                
                del features, features_cached
                gc.collect()
                profiler.take_snapshot("after_cleanup")
                
            except Exception as e:
                print(f"❌ 特征提取测试失败: {e}")
                return {}
        
        peak = profiler.get_peak_memory()
        growth = profiler.get_memory_growth()
        
        result = {
            "peak_memory_mb": peak.rss_mb,
            "memory_growth_rate": growth,
            "snapshots_count": len(profiler.snapshots)
        }
        
        self.results["feature_extraction"] = result
        profiler.print_summary()
        return result
    
    def benchmark_audio_rendering(self, file_path: str) -> Dict:
        """基准测试：音频渲染"""
        print("\n🔍 基准测试：音频渲染...")
        
        with memory_profiler("audio_rendering") as profiler:
            profiler.start_monitoring()
            
            try:
                from app.audio_analysis import AudioAnalyzer
                from app.parameter_inversion import ParameterInverter
                from app.audio_rendering import AudioRenderer
                
                # 准备数据
                analyzer = AudioAnalyzer()
                features = analyzer.analyze_features(file_path)
                
                inverter = ParameterInverter()
                style_params = inverter.invert_parameters(features, features, "A")
                
                renderer = AudioRenderer()
                
                profiler.take_snapshot("before_rendering")
                
                # 测试渲染
                output_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                output_file.close()
                
                metrics = renderer.render_audio(file_path, output_file.name, style_params)
                profiler.take_snapshot("after_rendering")
                
                # 清理
                os.unlink(output_file.name)
                del features, style_params, metrics
                gc.collect()
                profiler.take_snapshot("after_cleanup")
                
            except Exception as e:
                print(f"❌ 音频渲染测试失败: {e}")
                return {}
        
        peak = profiler.get_peak_memory()
        growth = profiler.get_memory_growth()
        
        result = {
            "peak_memory_mb": peak.rss_mb,
            "memory_growth_rate": growth,
            "snapshots_count": len(profiler.snapshots)
        }
        
        self.results["audio_rendering"] = result
        profiler.print_summary()
        return result
    
    def run_all_benchmarks(self) -> Dict:
        """运行所有基准测试"""
        print("🎵 音频处理内存基准测试")
        print("=" * 60)
        
        # 创建测试音频文件
        test_files = {
            "short": self.create_test_audio(5.0),    # 5秒
            "medium": self.create_test_audio(30.0),  # 30秒
            "long": self.create_test_audio(120.0),   # 2分钟
        }
        
        try:
            for duration, file_path in test_files.items():
                print(f"\n📁 测试文件: {duration} ({os.path.getsize(file_path) / 1024 / 1024:.1f} MB)")
                
                # 运行基准测试
                self.benchmark_audio_loading(file_path)
                self.benchmark_feature_extraction(file_path)
                self.benchmark_audio_rendering(file_path)
                
                # 保存结果
                self.results[f"{duration}_file"] = {
                    "file_size_mb": os.path.getsize(file_path) / 1024 / 1024,
                    "duration_sec": 5.0 if duration == "short" else (30.0 if duration == "medium" else 120.0)
                }
        
        finally:
            # 清理测试文件
            for file_path in test_files.values():
                if os.path.exists(file_path):
                    os.unlink(file_path)
        
        self.print_benchmark_summary()
        return self.results
    
    def print_benchmark_summary(self):
        """打印基准测试摘要"""
        print("\n📊 基准测试结果摘要:")
        print("=" * 60)
        
        for test_name, result in self.results.items():
            if "peak_memory_mb" in result:
                print(f"{test_name:20} | 峰值内存: {result['peak_memory_mb']:6.1f} MB | "
                      f"增长率: {result['memory_growth_rate']:6.2f} MB/s")

def main():
    """主函数"""
    print("🔍 音频处理内存优化分析工具")
    print("=" * 60)
    
    # 运行基准测试
    benchmark = AudioMemoryBenchmark()
    results = benchmark.run_all_benchmarks()
    
    # 保存结果到文件
    import json
    with open("memory_benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 基准测试结果已保存到: memory_benchmark_results.json")
    print("\n🎯 下一步优化建议:")
    print("1. 实现音频数据流式处理")
    print("2. 优化特征提取的内存使用")
    print("3. 改进缓存策略")
    print("4. 优化依赖注入容器生命周期")

if __name__ == "__main__":
    main()
