#!/usr/bin/env python3
"""
特征提取优化测试
验证音频特征提取过程的内存优化效果
"""

import sys
import os
import gc
import time
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

class FeatureExtractionOptimizationTest:
    """特征提取优化测试类"""
    
    def __init__(self):
        self.results = {}
    
    def create_test_audio(self, duration: float = 60.0, sample_rate: int = 48000) -> str:
        """创建测试音频文件"""
        print(f"创建测试音频: {duration}秒...")
        
        t = np.linspace(0, duration, int(duration * sample_rate), dtype=np.float32)
        
        # 创建复杂音频信号
        audio = 0.3 * np.sin(2 * np.pi * 440 * t)  # 基频
        audio += 0.2 * np.sin(2 * np.pi * 880 * t)  # 二次谐波
        audio += 0.1 * np.sin(2 * np.pi * 1320 * t)  # 三次谐波
        
        # 添加调制
        audio *= (1 + 0.3 * np.sin(2 * np.pi * 5 * t))
        
        # 添加噪声
        audio += 0.02 * np.random.normal(0, 1, len(t))
        
        # 添加包络
        envelope = np.exp(-t / (duration * 0.8))
        audio *= envelope
        
        # 保存到临时文件
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        sf.write(temp_file.name, audio, sample_rate)
        temp_file.close()
        
        file_size_mb = os.path.getsize(temp_file.name) / (1024 * 1024)
        print(f"✅ 创建完成: {temp_file.name} ({file_size_mb:.1f} MB)")
        
        return temp_file.name
    
    def test_stft_optimization(self, file_path: str) -> Dict:
        """测试STFT特征提取优化"""
        print("\n🔍 测试STFT特征提取优化...")
        
        results = {}
        
        # 测试传统方法
        print("  测试传统STFT方法...")
        try:
            with memory_profiler("traditional_stft") as profiler:
                profiler.start_monitoring()
                
                from app.audio_analysis import AudioAnalyzer
                analyzer = AudioAnalyzer()
                
                # 加载音频
                audio, sr = analyzer.load_audio(file_path)
                profiler.take_snapshot("after_load")
                
                # 使用回退方法进行STFT分析
                features = analyzer._analyze_stft_fallback(audio)
                profiler.take_snapshot("after_stft")
                
                del audio, features
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
        
        # 测试优化方法
        print("  测试优化STFT方法...")
        try:
            with memory_profiler("optimized_stft") as profiler:
                profiler.start_monitoring()
                
                from app.audio_features_optimized import MemoryOptimizedFeatureExtractor
                extractor = MemoryOptimizedFeatureExtractor()
                
                # 加载音频
                from app.audio_analysis import AudioAnalyzer
                analyzer = AudioAnalyzer()
                audio, sr = analyzer.load_audio(file_path)
                profiler.take_snapshot("after_load")
                
                # 使用优化方法进行STFT分析
                features = extractor.extract_stft_features_optimized(audio)
                profiler.take_snapshot("after_stft")
                
                del audio, features
                extractor.clear_cache()
                gc.collect()
                profiler.take_snapshot("after_cleanup")
            
            peak = profiler.get_peak_memory()
            growth = profiler.get_memory_growth()
            
            results["optimized"] = {
                "peak_memory_mb": peak.rss_mb,
                "memory_growth_rate": growth,
                "success": True
            }
            
            print(f"    优化方法峰值内存: {peak.rss_mb:.1f} MB")
            
        except Exception as e:
            print(f"    ❌ 优化方法失败: {e}")
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
            
            print(f"    💡 STFT内存减少: {memory_reduction:.1f} MB ({reduction_percent:.1f}%)")
        
        return results
    
    def test_mel_optimization(self, file_path: str) -> Dict:
        """测试Mel特征提取优化"""
        print("\n🎵 测试Mel特征提取优化...")
        
        results = {}
        
        # 测试传统方法
        print("  测试传统Mel方法...")
        try:
            with memory_profiler("traditional_mel") as profiler:
                profiler.start_monitoring()
                
                from app.audio_analysis import AudioAnalyzer
                analyzer = AudioAnalyzer()
                
                # 加载音频
                audio, sr = analyzer.load_audio(file_path)
                profiler.take_snapshot("after_load")
                
                # 使用回退方法进行Mel分析
                features = analyzer._analyze_mel_fallback(audio)
                profiler.take_snapshot("after_mel")
                
                del audio, features
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
        
        # 测试优化方法
        print("  测试优化Mel方法...")
        try:
            with memory_profiler("optimized_mel") as profiler:
                profiler.start_monitoring()
                
                from app.audio_features_optimized import MemoryOptimizedFeatureExtractor
                extractor = MemoryOptimizedFeatureExtractor()
                
                # 加载音频
                from app.audio_analysis import AudioAnalyzer
                analyzer = AudioAnalyzer()
                audio, sr = analyzer.load_audio(file_path)
                profiler.take_snapshot("after_load")
                
                # 使用优化方法进行Mel分析
                features = extractor.extract_mel_features_optimized(audio)
                profiler.take_snapshot("after_mel")
                
                del audio, features
                extractor.clear_cache()
                gc.collect()
                profiler.take_snapshot("after_cleanup")
            
            peak = profiler.get_peak_memory()
            growth = profiler.get_memory_growth()
            
            results["optimized"] = {
                "peak_memory_mb": peak.rss_mb,
                "memory_growth_rate": growth,
                "success": True
            }
            
            print(f"    优化方法峰值内存: {peak.rss_mb:.1f} MB")
            
        except Exception as e:
            print(f"    ❌ 优化方法失败: {e}")
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
            
            print(f"    💡 Mel内存减少: {memory_reduction:.1f} MB ({reduction_percent:.1f}%)")
        
        return results
    
    def test_combined_optimization(self, file_path: str) -> Dict:
        """测试组合特征提取优化"""
        print("\n🚀 测试组合特征提取优化...")
        
        results = {}
        
        # 测试传统组合方法
        print("  测试传统组合方法...")
        try:
            with memory_profiler("traditional_combined") as profiler:
                profiler.start_monitoring()
                
                from app.audio_analysis import AudioAnalyzer
                analyzer = AudioAnalyzer()
                
                # 加载音频
                audio, sr = analyzer.load_audio(file_path)
                profiler.take_snapshot("after_load")
                
                # 分别进行各种分析
                stft_features = analyzer._analyze_stft_fallback(audio)
                profiler.take_snapshot("after_stft")
                
                mel_features = analyzer._analyze_mel_fallback(audio)
                profiler.take_snapshot("after_mel")
                
                del audio, stft_features, mel_features
                gc.collect()
                profiler.take_snapshot("after_cleanup")
            
            peak = profiler.get_peak_memory()
            growth = profiler.get_memory_growth()
            
            results["traditional"] = {
                "peak_memory_mb": peak.rss_mb,
                "memory_growth_rate": growth,
                "success": True
            }
            
            print(f"    传统组合方法峰值内存: {peak.rss_mb:.1f} MB")
            
        except Exception as e:
            print(f"    ❌ 传统组合方法失败: {e}")
            results["traditional"] = {"success": False, "error": str(e)}
        
        # 测试优化组合方法
        print("  测试优化组合方法...")
        try:
            with memory_profiler("optimized_combined") as profiler:
                profiler.start_monitoring()
                
                from app.audio_features_optimized import MemoryOptimizedFeatureExtractor
                extractor = MemoryOptimizedFeatureExtractor()
                
                # 加载音频
                from app.audio_analysis import AudioAnalyzer
                analyzer = AudioAnalyzer()
                audio, sr = analyzer.load_audio(file_path)
                profiler.take_snapshot("after_load")
                
                # 使用优化方法进行组合分析
                all_features = extractor.extract_all_features_optimized(audio)
                profiler.take_snapshot("after_all_features")
                
                del audio, all_features
                extractor.clear_cache()
                gc.collect()
                profiler.take_snapshot("after_cleanup")
            
            peak = profiler.get_peak_memory()
            growth = profiler.get_memory_growth()
            
            results["optimized"] = {
                "peak_memory_mb": peak.rss_mb,
                "memory_growth_rate": growth,
                "success": True
            }
            
            print(f"    优化组合方法峰值内存: {peak.rss_mb:.1f} MB")
            
        except Exception as e:
            print(f"    ❌ 优化组合方法失败: {e}")
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
            
            print(f"    💡 组合特征内存减少: {memory_reduction:.1f} MB ({reduction_percent:.1f}%)")
        
        return results
    
    def run_feature_optimization_tests(self) -> Dict:
        """运行所有特征提取优化测试"""
        print("🔍 特征提取内存优化测试")
        print("=" * 60)
        
        # 创建测试文件
        test_file = self.create_test_audio(duration=60.0)  # 1分钟
        
        try:
            file_size_mb = os.path.getsize(test_file) / (1024 * 1024)
            print(f"\n📁 测试文件: {file_size_mb:.1f} MB")
            
            # 运行各项测试
            stft_results = self.test_stft_optimization(test_file)
            mel_results = self.test_mel_optimization(test_file)
            combined_results = self.test_combined_optimization(test_file)
            
            self.results = {
                "file_size_mb": file_size_mb,
                "stft": stft_results,
                "mel": mel_results,
                "combined": combined_results
            }
            
            self.print_optimization_summary()
            
        finally:
            # 清理测试文件
            if os.path.exists(test_file):
                os.unlink(test_file)
        
        return self.results
    
    def print_optimization_summary(self):
        """打印优化效果摘要"""
        print("\n📊 特征提取优化效果摘要:")
        print("=" * 60)
        
        for test_name, result in self.results.items():
            if isinstance(result, dict) and "improvement" in result:
                improvement = result["improvement"]
                print(f"{test_name.upper()}特征提取内存优化:")
                print(f"  内存减少: {improvement['memory_reduction_mb']:.1f} MB")
                print(f"  优化幅度: {improvement['reduction_percent']:.1f}%")
        
        print("\n🎯 优化建议:")
        print("1. 使用缓存的过滤器和窗口函数")
        print("2. 实现就地计算，减少临时数组创建")
        print("3. 使用float32替代float64")
        print("4. 及时清理临时变量和缓存")

def main():
    """主函数"""
    print("🔍 音频特征提取内存优化测试工具")
    print("=" * 60)
    
    # 运行优化测试
    test = FeatureExtractionOptimizationTest()
    results = test.run_feature_optimization_tests()
    
    # 保存结果
    import json
    with open("feature_optimization_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 测试结果已保存到: feature_optimization_results.json")

if __name__ == "__main__":
    main()
