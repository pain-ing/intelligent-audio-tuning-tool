#!/usr/bin/env python3
"""
流式处理优化测试
验证音频数据流式处理的内存优化效果
"""

import sys
import os
import gc
import time
import psutil
import numpy as np
import soundfile as sf
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

class StreamingOptimizationTest:
    """流式处理优化测试类"""
    
    def __init__(self):
        self.results = {}
    
    def create_large_test_audio(self, duration: float = 300.0, sample_rate: int = 48000) -> str:
        """创建大型测试音频文件（5分钟）"""
        print(f"创建大型测试音频: {duration}秒...")
        
        # 分块生成音频，避免内存问题
        chunk_duration = 30.0  # 30秒一块
        total_chunks = int(np.ceil(duration / chunk_duration))
        
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_file.close()
        
        # 生成第一块
        t_chunk = np.linspace(0, chunk_duration, int(chunk_duration * sample_rate), dtype=np.float32)
        audio_chunk = self._generate_audio_chunk(t_chunk, 0)
        
        # 写入第一块
        sf.write(temp_file.name, audio_chunk, sample_rate)
        
        # 追加其他块
        for i in range(1, total_chunks):
            current_duration = min(chunk_duration, duration - i * chunk_duration)
            t_chunk = np.linspace(0, current_duration, int(current_duration * sample_rate), dtype=np.float32)
            audio_chunk = self._generate_audio_chunk(t_chunk, i)
            
            # 追加到文件
            with sf.SoundFile(temp_file.name, 'r+') as f:
                f.seek(0, sf.SEEK_END)
                f.write(audio_chunk)
            
            del audio_chunk
            gc.collect()
        
        file_size_mb = os.path.getsize(temp_file.name) / (1024 * 1024)
        print(f"✅ 创建完成: {temp_file.name} ({file_size_mb:.1f} MB)")
        
        return temp_file.name
    
    def _generate_audio_chunk(self, t: np.ndarray, chunk_index: int) -> np.ndarray:
        """生成音频块"""
        # 创建复杂的音频信号
        base_freq = 440 + chunk_index * 10  # 基频随块变化
        
        audio = 0.3 * np.sin(2 * np.pi * base_freq * t)
        audio += 0.2 * np.sin(2 * np.pi * base_freq * 2 * t)  # 二次谐波
        audio += 0.1 * np.sin(2 * np.pi * base_freq * 3 * t)  # 三次谐波
        
        # 添加调制
        mod_freq = 5.0 + chunk_index * 0.5
        audio *= (1 + 0.3 * np.sin(2 * np.pi * mod_freq * t))
        
        # 添加噪声
        audio += 0.02 * np.random.normal(0, 1, len(t))
        
        # 包络
        envelope = np.exp(-t / (len(t) / 48000 * 0.8))
        audio *= envelope
        
        return audio.astype(np.float32)
    
    def test_traditional_vs_streaming_analysis(self, file_path: str) -> Dict:
        """对比传统方法和流式方法的内存使用"""
        print("\n🔍 对比分析方法的内存使用...")
        
        results = {}
        
        # 测试传统方法
        print("  测试传统分析方法...")
        try:
            with memory_profiler("traditional_analysis") as profiler:
                profiler.start_monitoring()
                
                from app.audio_analysis import AudioAnalyzer
                analyzer = AudioAnalyzer()
                
                profiler.take_snapshot("before_analysis")
                features = analyzer.analyze_features(file_path, use_streaming=False)
                profiler.take_snapshot("after_analysis")
                
                del features
                gc.collect()
                profiler.take_snapshot("after_cleanup")
            
            peak = profiler.get_peak_memory()
            growth = profiler.get_memory_growth()
            
            results["traditional"] = {
                "peak_memory_mb": peak.rss_mb,
                "memory_growth_rate": growth,
                "success": True
            }
            
            print(f"    传统方法峰值内存: {peak.rss_mb:.1f} MB")
            
        except Exception as e:
            print(f"    ❌ 传统方法失败: {e}")
            results["traditional"] = {"success": False, "error": str(e)}
        
        # 测试流式方法
        print("  测试流式分析方法...")
        try:
            with memory_profiler("streaming_analysis") as profiler:
                profiler.start_monitoring()
                
                from app.audio_analysis import AudioAnalyzer
                analyzer = AudioAnalyzer(max_memory_mb=256.0)  # 限制内存
                
                profiler.take_snapshot("before_analysis")
                features = analyzer.analyze_features(file_path, use_streaming=True)
                profiler.take_snapshot("after_analysis")
                
                del features
                gc.collect()
                profiler.take_snapshot("after_cleanup")
            
            peak = profiler.get_peak_memory()
            growth = profiler.get_memory_growth()
            
            results["streaming"] = {
                "peak_memory_mb": peak.rss_mb,
                "memory_growth_rate": growth,
                "success": True
            }
            
            print(f"    流式方法峰值内存: {peak.rss_mb:.1f} MB")
            
        except Exception as e:
            print(f"    ❌ 流式方法失败: {e}")
            results["streaming"] = {"success": False, "error": str(e)}
        
        # 计算改进
        if results["traditional"]["success"] and results["streaming"]["success"]:
            traditional_peak = results["traditional"]["peak_memory_mb"]
            streaming_peak = results["streaming"]["peak_memory_mb"]
            memory_reduction = traditional_peak - streaming_peak
            reduction_percent = (memory_reduction / traditional_peak) * 100
            
            results["improvement"] = {
                "memory_reduction_mb": memory_reduction,
                "reduction_percent": reduction_percent
            }
            
            print(f"    💡 内存减少: {memory_reduction:.1f} MB ({reduction_percent:.1f}%)")
        
        return results
    
    def test_traditional_vs_streaming_rendering(self, file_path: str) -> Dict:
        """对比传统方法和流式方法的渲染内存使用"""
        print("\n🎵 对比渲染方法的内存使用...")
        
        results = {}
        
        # 准备风格参数
        style_params = {
            "lufs": {"target_lufs": -16.0},
            "compression": {"enabled": True, "threshold_db": -20, "ratio": 2.0},
            "eq": [{"f_hz": 1000, "gain_db": 2.0, "q": 1.0, "type": "peaking"}]
        }
        
        # 测试传统方法
        print("  测试传统渲染方法...")
        try:
            with memory_profiler("traditional_rendering") as profiler:
                profiler.start_monitoring()
                
                from app.audio_rendering import AudioRenderer
                renderer = AudioRenderer()
                
                output_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                output_file.close()
                
                profiler.take_snapshot("before_rendering")
                metrics = renderer.render_audio(file_path, output_file.name, style_params, use_streaming=False)
                profiler.take_snapshot("after_rendering")
                
                os.unlink(output_file.name)
                del metrics
                gc.collect()
                profiler.take_snapshot("after_cleanup")
            
            peak = profiler.get_peak_memory()
            growth = profiler.get_memory_growth()
            
            results["traditional"] = {
                "peak_memory_mb": peak.rss_mb,
                "memory_growth_rate": growth,
                "success": True
            }
            
            print(f"    传统方法峰值内存: {peak.rss_mb:.1f} MB")
            
        except Exception as e:
            print(f"    ❌ 传统方法失败: {e}")
            results["traditional"] = {"success": False, "error": str(e)}
        
        # 测试流式方法
        print("  测试流式渲染方法...")
        try:
            with memory_profiler("streaming_rendering") as profiler:
                profiler.start_monitoring()
                
                from app.audio_rendering import AudioRenderer
                renderer = AudioRenderer(max_memory_mb=256.0)  # 限制内存
                
                output_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                output_file.close()
                
                profiler.take_snapshot("before_rendering")
                metrics = renderer.render_audio(file_path, output_file.name, style_params, use_streaming=True)
                profiler.take_snapshot("after_rendering")
                
                os.unlink(output_file.name)
                del metrics
                gc.collect()
                profiler.take_snapshot("after_cleanup")
            
            peak = profiler.get_peak_memory()
            growth = profiler.get_memory_growth()
            
            results["streaming"] = {
                "peak_memory_mb": peak.rss_mb,
                "memory_growth_rate": growth,
                "success": True
            }
            
            print(f"    流式方法峰值内存: {peak.rss_mb:.1f} MB")
            
        except Exception as e:
            print(f"    ❌ 流式方法失败: {e}")
            results["streaming"] = {"success": False, "error": str(e)}
        
        # 计算改进
        if results["traditional"]["success"] and results["streaming"]["success"]:
            traditional_peak = results["traditional"]["peak_memory_mb"]
            streaming_peak = results["streaming"]["peak_memory_mb"]
            memory_reduction = traditional_peak - streaming_peak
            reduction_percent = (memory_reduction / traditional_peak) * 100
            
            results["improvement"] = {
                "memory_reduction_mb": memory_reduction,
                "reduction_percent": reduction_percent
            }
            
            print(f"    💡 内存减少: {memory_reduction:.1f} MB ({reduction_percent:.1f}%)")
        
        return results
    
    def run_streaming_optimization_tests(self) -> Dict:
        """运行所有流式优化测试"""
        print("🚀 流式处理优化测试")
        print("=" * 60)
        
        # 创建大型测试文件
        test_file = self.create_large_test_audio(duration=180.0)  # 3分钟
        
        try:
            file_size_mb = os.path.getsize(test_file) / (1024 * 1024)
            print(f"\n📁 测试文件: {file_size_mb:.1f} MB")
            
            # 运行对比测试
            analysis_results = self.test_traditional_vs_streaming_analysis(test_file)
            rendering_results = self.test_traditional_vs_streaming_rendering(test_file)
            
            self.results = {
                "file_size_mb": file_size_mb,
                "analysis": analysis_results,
                "rendering": rendering_results
            }
            
            self.print_optimization_summary()
            
        finally:
            # 清理测试文件
            if os.path.exists(test_file):
                os.unlink(test_file)
        
        return self.results
    
    def print_optimization_summary(self):
        """打印优化效果摘要"""
        print("\n📊 流式处理优化效果摘要:")
        print("=" * 60)
        
        analysis = self.results.get("analysis", {})
        rendering = self.results.get("rendering", {})
        
        if "improvement" in analysis:
            print(f"特征分析内存优化:")
            print(f"  内存减少: {analysis['improvement']['memory_reduction_mb']:.1f} MB")
            print(f"  优化幅度: {analysis['improvement']['reduction_percent']:.1f}%")
        
        if "improvement" in rendering:
            print(f"音频渲染内存优化:")
            print(f"  内存减少: {rendering['improvement']['memory_reduction_mb']:.1f} MB")
            print(f"  优化幅度: {rendering['improvement']['reduction_percent']:.1f}%")
        
        print("\n🎯 优化建议:")
        print("1. 对于大于20MB的音频文件，自动启用流式分析")
        print("2. 对于大于30MB的音频文件，自动启用流式渲染")
        print("3. 根据可用内存动态调整块大小")
        print("4. 实现更智能的缓存策略")

def main():
    """主函数"""
    print("🔍 音频流式处理优化测试工具")
    print("=" * 60)
    
    # 运行优化测试
    test = StreamingOptimizationTest()
    results = test.run_streaming_optimization_tests()
    
    # 保存结果
    import json
    with open("streaming_optimization_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 测试结果已保存到: streaming_optimization_results.json")

if __name__ == "__main__":
    main()
